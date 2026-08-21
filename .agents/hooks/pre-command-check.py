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
        return

    # ----------------------------------------
    # AIによる事前の作業説明の有無を厳密に判定する
    # ----------------------------------------
    ai_pre_explanation = ""
    found_assistant_block = False
    aggregated_text = []

    for step in steps:
        step_type = step.get("type", "")
        source = step.get("source", "")
        content = step.get("content", "").strip()

        # PLANNER_RESPONSE (アシスタントの出力) を集約
        if source == "MODEL" and step_type == "PLANNER_RESPONSE":
            if content:  # 空のcontent（ツール呼び出しのみのステップなど）は無視して連続性を維持する
                found_assistant_block = True
                aggregated_text.append(content)
            continue

        # ユーザー入力（USER_INPUT）またはシステム応答（SYSTEM_RESPONSEなど）に達した場合
        if source != "MODEL":
            # すでにアシスタントのブロックを読み込み中の場合、そこで連続は途切れるため集約を終了
            if found_assistant_block:
                break

            # アシスタント発言が見つかるまでは読み飛ばして遡及を続ける
            continue

    # 逆順で収集したので、元の順序（時系列）に戻して結合
    aggregated_text.reverse()
    ai_pre_explanation = "\n".join(aggregated_text)

    # 単なる文字数チェック（`has_enough_length`）だけでは、AIが英語のログやコードを垂れ流して無言実行を強行突破してしまう可能性がある。
    # コア要求である「コマンド実行許可を求める前に『実行内容を日本語で説明する』こと」をシステム的に担保するため、
    # 正規表現を用いてテキスト内に日本語（ひらがな・カタカナ・漢字）が実際に含まれているかを判定の必須条件としている。
    has_enough_length = len(ai_pre_explanation) > 30
    has_japanese = bool(re.search(r"[ぁ-んァ-ン一-龥]", ai_pre_explanation))

    is_approved = has_enough_length and has_japanese

    if is_approved:
        # 事前説明が同一ステップ内で十分に行われている場合は、コマンドの実行を許可（allow）する
        return
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
