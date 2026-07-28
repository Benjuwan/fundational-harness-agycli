import sys
import json
import os
import re

# 検知対象となるスクリプト実行コマンド
cmd_lists = ["npm", "npx", "python", "python3", "sh", "bash", "./", "node", "docker"]


# 「コマンド実行許可を求める前に『実行内容を日本語で説明する』こと」を実現する矯正層（PreToolUse フック： ツールが実行される前に実行されるハンドラ）ファイル
def main():
    try:
        # Antigravity CLIから標準入力(stdin)経由で渡されるコンテキスト情報（JSON）を読み込む
        input_data = json.load(sys.stdin)

    except json.JSONDecodeError:
        # JSONのパースに失敗した場合は、安全策として実行を明示的に拒否（deny）する
        print(json.dumps({"decision": "deny", "reason": "Failed to parse json file."}))
        return

    # コンテキスト情報から会話ログ（トランスクリプト）のファイルパスを取得する
    transcript_path = input_data.get("transcriptPath")
    if not transcript_path or not os.path.exists(transcript_path):
        # ログファイルが存在しない場合はチェックできないため安全策として実行を明示的に拒否（deny）する
        print(json.dumps({"decision": "deny", "reason": "Transcript file not found."}))
        return

    steps = []
    try:
        # トランスクリプトファイルを末尾から読み込み、最新の15件のログステップを抽出する
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 最新の会話履歴から遡るために逆順でループ
            for line in reversed(lines):
                try:
                    steps.append(json.loads(line))
                    # 直近の会話の流れを把握するには15件で十分なため、それ以上は読み込まない
                    if len(steps) >= 15:
                        break
                except json.JSONDecodeError:
                    continue
    except Exception:
        # 意図せぬ例外発生時は安全策として実行を明示的に拒否（deny）する
        deny_msg = "Exception: Missing prior explanation. Output text to user BEFORE calling this tool."
        print(json.dumps({"decision": "deny", "reason": deny_msg}))
        return

    # ----------------------------------------
    # 呼び出されたツールが「事前説明を必須とする重要なアクション」か判定する
    # ----------------------------------------
    tool_call = input_data.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    arguments = tool_call.get("args", {})

    is_important_action = False

    if tool_name == "invoke_subagent":
        # サブエージェントの起動は重要アクションとする
        is_important_action = True
    elif tool_name == "run_command":
        # コマンド実行の場合、内容によって判定する
        cmd_line = str(arguments.get("CommandLine", "")).lower()
        bypass_sandbox = arguments.get("BypassSandbox", False)

        # JSONのブール値として渡されるが、念のため文字列の場合も考慮
        if isinstance(bypass_sandbox, str):
            bypass_sandbox = bypass_sandbox.lower() == "true"

        # 条件1: サンドボックス回避フラグ（BypassSandbox: true）がある場合
        if bypass_sandbox:
            is_important_action = True

        # 条件2: 通常のスクリプト実行コマンドが含まれる場合
        elif any(kw in cmd_line for kw in cmd_lists):
            is_important_action = True

    # 重要なアクションではない（単なる`ls`など）場合は、説明チェックをスキップして即許可する
    if not is_important_action:
        # 重大な変更ではない場合は自動許可
        print(json.dumps({"decision": "allow"}))
        return

    # ----------------------------------------
    # AIによる事前の作業説明の有無を厳密に判定する
    # ----------------------------------------
    ai_pre_explanation = ""

    # stepsには最新のログから古いログへ降順(reversed)で格納されている
    # ログを遡り、「現在まさにツールを呼び出そうとしているAIの発言（PLANNER_RESPONSE）」を1つだけ取得する。
    #
    # 【同期遅延対策】
    # PreToolUse フック発火時、現在のステップ（AIの応答）は transcript（会話ログ）にまだ書き込まれていない。
    # そのため、transcript の最新エントリは1つ前のステップである可能性がある。
    # もし直近に USER_INPUT（新しいユーザー指示）があり、その後に PLANNER_RESPONSE（AI応答文）がない場合、
    # それ以前の PLANNER_RESPONSE は別のタスクに対する説明であり、stale（無効）と判定する。
    # この deny（＝会話ログのかさ増し処理）により、現在のステップが transcript に書き込まれた後のリトライで正しく検証できる。
    for step in steps:
        step_type = step.get("type", "")

        # USER_INPUT を PLANNER_RESPONSE より先に検出した場合:
        # → 直近のユーザー指示の後に AI の説明がない = stale（無効）
        if step_type == "USER_INPUT":
            user_content = step.get("content", "")
            if "<ADDITIONAL_METADATA>" in user_content:
                user_content = user_content.split("<ADDITIONAL_METADATA>")[0]
            if "<USER_REQUEST>" in user_content:
                user_content = user_content.replace("<USER_REQUEST>", "").replace(
                    "</USER_REQUEST>", ""
                )
            # `strip`: 文字列の先頭と末尾から不要な空白文字（スペース、タブ、改行など）や指定文字を削除
            user_content = user_content.strip()

            # 短い承認応答（"y", "ok", "はい" 及び、それらの意図を補足するユーザー入力など）は新しい指示ではなく、
            # 前の PLANNER_RESPONSE への同意なのでスキップして走査を続行する
            if len(user_content) <= 75:
                continue

            # 実質的な新しい指示を検出 → これ以前の PLANNER_RESPONSE は別タスクの説明
            # ai_pre_explanation を空のまま break し、deny に落とす
            break

        # AIによる入力かどうかを判定
        if step.get("source") == "MODEL" and step_type == "PLANNER_RESPONSE":
            # 【チャンク実行（ユーザーの入力を挟まずAIが自律的に連続アクションを起こすフェーズ）時の不正受給（テキスト使い回し）防止】
            # 過去のログを遡った際、そのステップに既に `tool_calls`（過去に実行したツールの履歴）が紐づいていた場合、
            # そのテキストは「前回のコマンド実行時に消費された説明」であると判定する。
            # これをスキップ（continue）することで、連続実行時に無言のまま過去の貯金で許可UIが出てしまうバグを防ぐ。
            tool_calls = step.get("tool_calls", [])
            if len(tool_calls) > 0:
                continue

            # 今回のツール呼び出しのために出力された（未消費の）テキストを整形してから取得する
            ai_pre_explanation = step.get("content", "").strip()

            # 【重要】未消費のPLANNER_RESPONSEを見つけた時点で必ずループを抜ける。
            # 過去のターンの発言（貯金）を遡って拾い上げないようにするための厳密な強制措置。
            break

    # 単なる文字数チェック（`has_enough_length`）だけでは、AIが英語のログやコードを垂れ流して無言実行を強行突破してしまう可能性がある。
    # コア要求である「コマンド実行許可を求める前に『実行内容を日本語で説明する』こと」をシステム的に担保するため、
    # 正規表現を用いてテキスト内に日本語（ひらがな・カタカナ・漢字）が実際に含まれているかを判定の必須条件としている。
    has_enough_length = len(ai_pre_explanation) > 30
    has_japanese = bool(re.search(r"[ぁ-んァ-ン一-龥]", ai_pre_explanation))

    is_approved = has_enough_length and has_japanese

    if is_approved:
        # 事前説明が同一ステップ内で十分に行われている場合は、コマンドの実行を許可（allow）する
        print(json.dumps({"decision": "allow"}))
    else:
        # 事前説明がない、または30文字未満の場合は実行を明確に拒否（deny）し、AIへ即時フィードバックを返す。
        # 【プロンプトインジェクション（通知）の意図】
        # AI自身に「あ、テキストを出し忘れたからリトライしよう」と自律的な行動矯正を促すための仕組み。

        if tool_name == "invoke_subagent":
            # サブエージェント起動時の専用拒否メッセージ
            deny_msg = (
                "【カスタムフック (pre-command-check.py) による明示的拒否】\n"
                "エラー「subagent not found or not allowed to be invoked」の原因は、システムの不具合ではなく、このカスタムフックによる意図的な実行ブロックです。\n"
                "■ 拒否理由:\n"
                "ツール実行と同じターン内で、事前の日本語説明（30文字以上）が行われていません。\n"
                "■ 必須ワークフロー（タスクフローの強制）:\n"
                "1. まず実行内容を日本語で説明してターンを終了する\n"
                "2. ユーザーから承認（y など）を得る（※）\n"
                "※ここで承認を得ても、その後のOS権限制限により実行不可になるケースが多々あるので、`npm`, `npx`, `python`,`python3`, `git` など特定コマンドにおけるサンドボックスのバイパス許可（権限制御のバイパス許可）も合わせて求めておく\n"
                "3. その後、改めてツールを起動する"
            )
            print(json.dumps({"decision": "deny", "reason": deny_msg}))
        else:
            # その他のツール呼び出し時
            notify_msg = (
                "【カスタムフックによる明示的拒否】\n"
                "コマンドの事前説明が確認できませんでした。\n"
                "ユーザーが安心して承認できるよう、ツールを呼び出す前に、"
                "必ず「次に実行するコマンドとその目的」を日本語テキストで出力し、"
                "かつ文末に「〜してもよろしいですか？（y/n）」と明示的に問いかけてください。"
            )
            print(json.dumps({"decision": "deny", "reason": notify_msg}))


if __name__ == "__main__":
    main()
