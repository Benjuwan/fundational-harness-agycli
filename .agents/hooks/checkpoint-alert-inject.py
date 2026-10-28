import sys
import json
from checkpoint_utils import detect_checkpoint, check_invocation_num


# コンテキストの自動圧縮を確認して警告を通知（AIへ文章インジェクション）するためのフック
def main():
    try:
        # Antigravity CLIから標準入力(stdin)経由で渡されるコンテキスト情報（JSON）を読み込む
        input_data = json.load(sys.stdin)
    except Exception as e:
        sys.stderr.write(f"Error reading stdin: {e}\n")
        input_data = {}

    # コンテキスト情報から会話ログ（トランスクリプト）のファイルパスを取得する
    transcript_path = input_data.get("transcriptPath")

    # 初回呼び出し・起動時か確認するためのフラグ
    is_first_invocation = check_invocation_num(input_data)

    # 共通ユーティリティを使ってコンテキストの自動圧縮を検知し、状態を保存する
    checkpoint_detected = detect_checkpoint(
        transcript_path, ".last_checkpoint_state", is_first_invocation
    )

    # コンテキストの自動圧縮が発生している場合、適切なペイロードを作成する
    if checkpoint_detected:
        inject_payload = {
            "injectSteps": [
                {
                    "ephemeralMessage": "【緊急】コンテキストの自動圧縮を確認しました。これはAIの作業パフォーマンスが低下する前兆です。直ちにユーザーへ報告して、作業継続か作業停止（引き継ぎドキュメントを更新して新しいセッションへ切替）かの判断を仰いでください。"
                }
            ]
        }
        print(json.dumps(inject_payload))
    else:
        # コンテキストの自動圧縮が発生していない場合は空の配列を返す（何もしない）
        print(json.dumps({"injectSteps": []}))


if __name__ == "__main__":
    main()
