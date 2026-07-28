import sys
import os
import json
from checkpoint_utils import detect_checkpoint, check_invocation_num


# 「コマンド実行許可を求める前に『実行内容を日本語で説明する』ことと『強制的にルールファイルをコンテキストへ注入する』こと」を実現する予防層（PreInvocation フック： モデル呼び出し前に実行される）ファイル
#
# 【実装意図: 動的インジェクションによる「Lost in the middle」対策】
# LLMには「Lost in the middle（中間情報の忘却現象）」という特性があり、長いコンテキストを処理する際、
# アテンション（注意力）が「U字型の記憶カーブ」を描きます。つまり、情報の最初（Primacy bias）と
# 最後（Recency bias）に注意が偏り、中間に埋もれたシステムルールは無視されやすくなります。
# そのため、AIが目前のタスクに集中すると、冒頭の「事前確認ルール」は中間に押し出されて形骸化してしまいます。
# これを物理的に防ぐため、毎ターンの推論直前（コンテキストの最後尾）に最も優先すべき絶対ルールを
# 動的に注入（Inject）し、「Recency bias」を突いて強制的にルールを再認識させます。


def main():
    try:
        # 標準入力（stdin）からシステムのフックペイロード（JSON）をパースする
        input_data = json.load(sys.stdin)
    except Exception:
        input_data = {}

    # 初回呼び出し・起動時か確認するためのフラグ
    is_first_invocation = check_invocation_num(input_data)

    # コンテキスト情報から会話ログ（トランスクリプト）のファイルパスを取得する
    transcript_path = input_data.get("transcriptPath")

    # 共通ユーティリティを使ってコンテキストの自動圧縮を検知し、状態を独立して保存・更新する
    checkpoint_detected = detect_checkpoint(
        transcript_path, ".last_pre_invocation_state", is_first_invocation
    )

    # PreInvocation フックは「毎回の思考・推論の直前」に発火するため、
    # 【コンテキストの自動圧縮が確認された場合のみ】ルールを注入し、以降のターンの不要な再読み込みによるコンテキストの圧迫を防ぐ
    if checkpoint_detected:
        # スクリプト自身の配置場所を基準に絶対パスを取得する（CWDの影響を排除）
        base_dir = os.path.dirname(os.path.abspath(__file__))
        rule_path = os.path.join(base_dir, "..", "rules", "workflow.md")
        content = "Workflow not found."
        if os.path.exists(rule_path):
            with open(rule_path, "r", encoding="utf-8") as f:
                content = f.read()  # workflow.md の内容

        # [HOOK INJECTION]: workflow.md の内容をAIに読ませる（Prompt Injection）
        inject_payload = {
            "injectSteps": [
                {
                    # `f"""..."""`のマルチライン文字列で記述すると、Pythonコード上のインデント（スペース）がそのままメッセージに含まれてしまって出力テキストに余計な空白が入ってしまうため、
                    # 文字列の結合（括弧による暗黙的な結合）で、余計な空白が入らないように整形している
                    "ephemeralMessage": (
                        "CRITICAL RULE: Before executing a command such as “run_command” or “invoke_subagent,” or before calling a subagent, "
                        "you MUST output a clear explanation of your intended action in Japanese text. "
                        "Silent tool calls are strictly forbidden and will be blocked.\n"
                        "And be sure to follow the rules (Workflow Rules) below.\n"
                        f"[HOOK INJECTION] Workflow Rules:\n\n{content}"
                    )
                }
            ]
        }
        print(json.dumps(inject_payload))
    else:
        # コンテキストの自動圧縮が確認されない場合は injectSteps に空配列を指定することでコンテキスト量を節約する
        print(json.dumps({"injectSteps": []}))


if __name__ == "__main__":
    main()
