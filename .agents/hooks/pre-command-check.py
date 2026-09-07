import sys
import json
import os
import re

# 検知対象となるスクリプト実行コマンド
cmd_lists = ["npm", "npx", "python", "python3", "sh", "bash", "./", "node", "docker"]

# 肯定応答の正規表現パターン（前後の空白・記号除去後に照合）
AFFIRMATIVE_PATTERN = re.compile(
    r"^(y|ok|おｋ|了解|了解です|承知|承知しました|承認|実行して|実行してください|進めて|進めてください|お願いします|おねがいします|はい|はい、お願いします|はいお願いします)$",
    re.IGNORECASE,
)

# 否定・中止の正規表現パターン
NEGATIVE_PATTERN = re.compile(
    r"(no|stop|待って|やめて|中止|一旦中断して|停止|ダメ|だめ|いいえ|キャンセル)",
    re.IGNORECASE,
)

# 提案ステップでの確認・問いかけパターン
CONFIRMATION_PATTERN = re.compile(
    r"(よろしいですか|よろしいでしょうか|いかがでしょうか|\(y/n\)|y/n|確認|進めてもいい|進めてもよろしい|実行してもいい|実行してもよろしい|実行してよい|問題ないでしょうか|問題ありませんでしょうか)",
    re.IGNORECASE,
)

# サブエージェント名のリスト
SUBAGENT_NAMES = [
    "handwritten-doc-extractor",
    "image-processor",
    "implementer-agent",
    "qa-auditor",
    "task-executor",
]

# サブエージェント検知用シグネチャ
SUBAGENT_SIGNATURES = [
    re.compile(r"【ミッション・ブリーフ", re.IGNORECASE),
    re.compile(r"ミッション・ブリーフ", re.IGNORECASE),
    re.compile(r"name:\s*[a-zA-Z0-9_\-\.]+\s*\n(?:description:|kind:)", re.IGNORECASE),
    # 正規表現のエスケープを保ったまま変数をきれいに展開するために `fr` を使用
    re.compile(rf"name:\s*({'|'.join(SUBAGENT_NAMES)})", re.IGNORECASE),
]


def is_subagent_environment(lines):
    """
    トランスクリプト（会話ログ）の先頭部分等からサブエージェント環境であるかを自動識別する。
    """
    # 先頭10行および末尾5行を走査
    check_lines = lines[:10] + (lines[-5:] if len(lines) > 10 else [])
    for line in check_lines:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            entry = json.loads(line_str)  # 不要な文字列を排除した会話ログをパース
            content = entry.get("content", "")  # 会話ログの中身を取得
            if isinstance(content, str):
                for sig in SUBAGENT_SIGNATURES:
                    if sig.search(
                        content
                    ):  # サブエージェント検知用シグネチャに一致するかどうかを判定
                        return True
        except Exception:
            continue
    return False


def clean_user_input(text: str) -> str:
    """ユーザー入力から前後の記号や空白を取り除いて正規化する"""
    text = text.strip()
    # 前後の記号（.,!?、。-~など）を除去
    text = re.sub(r"^[\s\.\,\!\?、。\-~〜/]+|[\s\.\,\!\?、。\-~〜/]+$", "", text)
    return text.strip()


def check_text_validity(text: str) -> bool:
    """30文字以上かつ日本語（ひらがな・カタカナ・漢字）が含まれているか検証"""
    has_enough_length = len(text.strip()) >= 30
    has_japanese = bool(re.search(r"[ぁ-んァ-ン一-龥]", text))
    return has_enough_length and has_japanese


def output_deny(tool_name: str, subagent_mode: bool) -> None:
    """状況に応じた適切な拒否メッセージを出力する"""
    if subagent_mode:
        deny_msg = (
            "【カスタムフック (pre-command-check.py) による明示的拒否（サブエージェント自律実行）】\n"
            "ツールの無言実行は禁止されています。\n"
            "■ 必須アクション:\n"
            "ツール呼び出しを行う前に、同一ターン内で「これから何を行うか、その目的と手順」を"
            "30文字以上の日本語テキストで必ず出力してください。"
        )
    elif tool_name in ("invoke_subagent", "Task", "Agent"):
        deny_msg = (
            "【カスタムフック (pre-command-check.py) による明示的拒否】\n"
            "サブエージェント起動の事前説明、またはユーザー承認が確認できませんでした。\n"
            "■ 必須ワークフロー（タスクフローの強制）:\n"
            "1. サブエージェントを起動する前に、起動するサブエージェントの役割と指示内容を30文字以上の日本語で説明し、\n"
            "   文末で「〜してもよろしいですか？（y/n）」とユーザーに承認を求めてターンを終了してください。\n"
            "2. ユーザーから承認（y など）を得た後、サブエージェントを起動してください。"
        )
    else:
        deny_msg = (
            "【カスタムフック (pre-command-check.py) による明示的拒否】\n"
            "コマンド実行の事前説明、またはユーザー承認が確認できませんでした。\n"
            "■ 必須ワークフロー（HITLの原則）:\n"
            "1. ツールを実行する前に、必ず「実行するコマンドとその目的」を30文字以上の日本語テキストで出力し、\n"
            "   文末で「〜してもよろしいですか？（y/n）」とユーザーに承認を求めてターンを終了してください。\n"
            "2. ユーザーから承認（y など）を得た後、ツールを実行してください。\n"
            "※同一ターン内で30文字以上の十分な日本語説明を行って実行することも可能です。"
        )
    print(json.dumps({"decision": "deny", "reason": deny_msg}))


# 「コマンド実行許可を求める前に『実行内容を日本語で説明する』こと」を実現する矯正層（PreToolUse フック： ツールが実行される前に実行されるハンドラ）ファイル
def main():
    try:
        # Antigravity CLIから標準入力(stdin)経由で渡されるコンテキスト情報（JSON）を読み込む
        input_data = json.load(sys.stdin)
    except Exception:
        # JSONのパースに失敗した場合は、安全策として実行を明示的に拒否（deny）する
        print(json.dumps({"decision": "deny", "reason": "Failed to parse json file."}))
        return

    # コンテキスト情報から会話ログ（トランスクリプト）のファイルパスを取得する
    transcript_path = input_data.get("transcriptPath") or input_data.get(
        "transcript_path"
    )
    if not transcript_path or not os.path.exists(transcript_path):
        # ログファイルが存在しない場合はチェックできないため安全策として実行を明示的に拒否（deny）する
        print(json.dumps({"decision": "deny", "reason": "Transcript file not found."}))
        return

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()
    except Exception:
        deny_msg = "Exception: Failed to read transcript file."
        print(json.dumps({"decision": "deny", "reason": deny_msg}))
        return

    # ----------------------------------------
    # 呼び出されたツールが「事前説明を必須とする重要なアクション」か判定する
    # ----------------------------------------
    tool_call = input_data.get("toolCall", {}) or {}
    tool_name = tool_call.get("name", "") or input_data.get("tool_name", "")
    arguments = tool_call.get("args", {}) or input_data.get("tool_input", {}) or {}

    is_important_action = False

    if tool_name in ("invoke_subagent", "Task", "Agent"):
        # サブエージェントの起動は重要アクションとする
        is_important_action = True
    elif tool_name in ("run_command", "Bash"):
        # コマンド実行の場合、内容によって判定する（コマンドライン引数からコマンドラインの内容を取得して小文字に整形）
        cmd_line = str(
            arguments.get("CommandLine", "") or arguments.get("command", "")
        ).lower()
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
        return

    # ----------------------------------------
    # サブエージェント環境の自動識別
    # ----------------------------------------
    subagent_mode = is_subagent_environment(raw_lines)

    # ----------------------------------------
    # ステップの逆順走査とステートマシンによる解析
    # ----------------------------------------
    parsed_steps = []
    # raw_lines: 会話ログの文字列データ（`readlines()`により配列として取得）
    for line in reversed(raw_lines):
        line_str = line.strip()
        if not line_str:
            continue
        try:
            parsed_steps.append(json.loads(line_str))
            if len(parsed_steps) >= 30:
                break
        except json.JSONDecodeError:
            continue

    # 逆順で走査しながら以下のブロックを特定する:
    # 1. current_model_texts (Turn N): 直近のユーザー入力より後にあるMODEL発言群
    # 2. last_user_step (Turn N-1): 直近のユーザー入力ステップ
    # 3. proposal_model_texts (Turn N-2): 直近ユーザー入力より前、さらにその前のユーザー入力までのMODEL発言群

    current_model_texts = []
    last_user_step = None
    proposal_model_texts = []

    phase = 0  # 0: Turn N 探索中, 1: Turn N-1 完了済みで Turn N-2 探索中, 2: 完了

    for step in parsed_steps:
        source = step.get("source", "")
        step_type = step.get("type", "")
        content = step.get("content", "")
        if not isinstance(content, str):
            content = ""
        content = content.strip()

        is_user = (
            source in ("USER_EXPLICIT", "USER") or step_type == "USER_INPUT"
        ) and source != "MODEL"
        is_model = source == "MODEL"

        if phase == 0:
            if is_user:
                # 最初のユーザー入力に遭遇 -> Turn N 終了、Turn N-1 として記録
                last_user_step = step
                phase = 1
                continue
            elif is_model:
                if content:
                    current_model_texts.append(content)
            # TOOL_OUTPUT や SYSTEM 等はスキップ

        elif phase == 1:
            if is_user:
                # さらに前のユーザー入力に遭遇 -> Turn N-2 終了
                phase = 2
                break
            elif is_model:
                if content:
                    proposal_model_texts.append(content)

    current_model_texts.reverse()
    current_text = "\n".join(current_model_texts).strip()

    proposal_model_texts.reverse()
    proposal_text = "\n".join(proposal_model_texts).strip()

    # ----------------------------------------
    # 判定分岐
    # ----------------------------------------

    # 判定1: 同一ターン説明型（30文字以上かつ日本語あり）
    # サブエージェント環境でもメインエージェント環境でも、同一ターンで十分な説明があれば即PASS
    if check_text_validity(current_text):
        return

    # 判定2: サブエージェント環境での無言・説明不足実行
    # サブエージェントはユーザー承認UIを持たないため、同一ターン説明が不十分な時点でブロック
    if subagent_mode:
        output_deny(tool_name, subagent_mode=True)
        return

    # 判定3: メインエージェント用 2ターンHITL照合ステートマシン
    # 直前のユーザー入力が存在しない場合は無言実行とみなして拒否
    if not last_user_step:
        output_deny(tool_name, subagent_mode=False)
        return

    user_content = last_user_step.get("content", "")
    if not isinstance(user_content, str):
        user_content = ""

    # ユーザー入力文字（記号や改行などを取り除いた文字列）
    cleaned_user = clean_user_input(user_content)

    # 3-a. ユーザーによる否定・中止・質問等の検知（暴走防止）
    if NEGATIVE_PATTERN.search(cleaned_user):
        output_deny(tool_name, subagent_mode=False)
        return

    # 3-b. 明確な肯定応答（y, yes, ok, 了解等）であるか検証
    if not AFFIRMATIVE_PATTERN.match(cleaned_user):
        output_deny(tool_name, subagent_mode=False)
        return

    # 3-c. 肯定応答の場合、提案ステップ (Turn N-2) を検証
    # 提案が30文字以上＋日本語あり、かつ確認問いかけが含まれているか
    if check_text_validity(proposal_text) and CONFIRMATION_PATTERN.search(
        proposal_text
    ):
        # HITLフロー完了として実行を許可
        return
    else:
        # 提案説明が不十分、または問いかけがない場合は拒否
        output_deny(tool_name, subagent_mode=False)
        return


if __name__ == "__main__":
    main()
