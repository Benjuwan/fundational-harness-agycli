import sys
import os
import json
import argparse

# 許可されたサブエージェントのホワイトリスト。
# 実際に .agents/agents/ 配下に定義ファイルが存在するものだけを登録する。
ALLOWED_SUB_AGENTS = [
    "task-executor",
    "implementer-agent",
    "image-processor",
    "qa-auditor",
]


# カスタムサブエージェント起動時に、当該サブエージェントを組み込みサブエージェント（`self`）へオーバーソウル（憑依）させるためのスクリプト。
# ここで扱う名前は、実際に .agents/agents/ 配下に存在する定義ファイル名と一致させる。
def generate_prompt(sub_agent_name, recent_log, user_prompt):
    if sub_agent_name not in ALLOWED_SUB_AGENTS:
        raise ValueError(
            f"サブエージェント `{sub_agent_name}` はスクリプトファイル内のホワイトリストに登録されていません。"
        )

    # プロジェクトルートからの絶対パスとして解決
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    agent_file_path = os.path.join(
        project_root, ".agents", "agents", f"{sub_agent_name}.md"
    )

    # サブエージェントの定義ファイル（.md）の有無を確認
    if not os.path.exists(agent_file_path):
        raise FileNotFoundError(
            f"サブエージェント `{sub_agent_name}` の定義ファイルが見つかりません: {agent_file_path}"
        )

    # ファイルが存在すれば、内容を読み込む
    with open(agent_file_path, "r", encoding="utf-8") as f:
        agent_brief = f.read()

    # プロンプトとして出力するためのテンプレートに、サブエージェントの定義内容を埋め込む
    final_prompt = (
        "【ミッション・ブリーフ（役割と制約）】\n"
        "以下はあなたの役割と絶対遵守すべき制約事項です。必ず読み込み、この指示に従って行動してください。\n"
        "---\n"
        f"{agent_brief}\n"
        "---\n"
        "\n"
        "【直近のコンテキスト（ログ）】\n"
        "以下はこれまでの作業経緯やログです。状況把握のために使用してください。\n"
        "---\n"
        f"{recent_log}\n"
        "---\n"
        "\n"
        "【ユーザーからの指示（タスク）】\n"
        "以下の指示に基づき、あなたの役割を全うしてタスクを実行してください。\n"
        "---\n"
        f"{user_prompt}\n"
        "---\n"
    )
    return final_prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="サブエージェントへのインジェクション用プロンプトを生成します。"
    )
    parser.add_argument("sub_agent_name", help="呼び出すサブエージェント名")
    parser.add_argument(
        "--log", help="直近ログのテキスト、またはファイルパス", default="特になし"
    )
    parser.add_argument(
        "--prompt", help="ユーザー入力のテキスト、またはファイルパス", required=True
    )
    parser.add_argument(
        "--out",
        help="出力先ファイルパス。指定された場合はUTF-8エンコーディングで保存します。",
        default=None,
    )

    # 引数を解析し、変数argsに格納
    args = parser.parse_args()

    # 引数がファイルパスであれば内容を読み込む、そうでなければそのままテキストとして扱う
    def resolve_input(input_val):
        if os.path.isfile(input_val):
            # パストラバーサル対策：読み込みを許可する基準ディレクトリを設定
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            gemini_root = os.path.expanduser("~/.gemini")

            # 対象ファイルの絶対パスを取得し、正規化する
            target_path = os.path.abspath(input_val)

            # target_path が project_root または gemini_root 配下に存在するか厳密にチェック
            is_allowed = target_path.startswith(
                project_root + os.sep
            ) or target_path.startswith(gemini_root + os.sep)

            if not is_allowed:
                raise PermissionError(
                    f"セキュリティエラー: 許可されたディレクトリ外の機密ファイル読み込みは禁止されています ({input_val})"
                )

            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = input_val
        # 改行コードの正規化（CRLF/CR を LF に統一）
        return content.replace("\r\n", "\n").replace("\r", "\n")

    def format_log_for_llm(log_text):
        """ログがJSONL形式の場合、LLMが読みやすいテキストに整形する"""
        formatted_lines = []
        is_jsonl = False

        for line in log_text.splitlines():
            # `strip`: 文字列の先頭と末尾から不要な空白文字（スペース、タブ、改行など）や指定文字を削除
            if not line.strip():
                continue
            try:
                # jsonオブジェクトを格納
                data = json.loads(line)
                is_jsonl = True
                if isinstance(data, dict):
                    # 役割や文章内容などよくあるキーから話者やイベントの種類を特定
                    role = data.get("role", data.get("source", data.get("type", "LOG")))
                    content = data.get(
                        "content",
                        data.get("message", json.dumps(data, ensure_ascii=False)),
                    )
                    # 「役割（改行）文章内容という（改行）」という文章形式に変換
                    formatted_lines.append(f"[{role}]\n{content}\n")
                else:
                    # jsonオブジェクト（辞書データ構造）ではない場合、そのまま文字列として追加
                    formatted_lines.append(str(data))
            except json.JSONDecodeError:
                # JSONとしてパースできないプレーンテキスト行はそのまま維持
                formatted_lines.append(line)

        if is_jsonl:
            # jsonオブジェクト（辞書データ構造）だった場合は改行追加や整形処理を行った文字列として返す
            return "\n".join(formatted_lines).strip()
        else:
            return log_text.strip()

    try:
        recent_log_text = resolve_input(args.log)
        user_prompt_text = resolve_input(args.prompt)

        # ログがJSONL構造であればLLMが理解しやすいプレーンテキストにパースする
        recent_log_text = format_log_for_llm(recent_log_text)

        # 組み込みエージェントにオーバーソウル（憑依）させるためのプロンプト（サブエージェント起動時に組み込みエージェントへ渡すためのプロンプトインジェクション用文章を生成）
        over_soul_prompt = generate_prompt(
            args.sub_agent_name, recent_log_text, user_prompt_text
        )

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(over_soul_prompt)
            print(f"プロンプトを {args.out} にUTF-8で保存しました。")
        else:
            print(over_soul_prompt)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
