import os
import sys
import json
import tempfile  # 一時ファイルや一時ディレクトリを安全に作成・削除できる標準ライブラリ


def detect_checkpoint(transcript_path, state_file_name, is_first_invocation=False):
    """
    トランスクリプトの行数をチェックし、前回のチェック時からコンテキストの自動圧縮が発生したかを判定するユーティリティPythonスクリプト。判定後、現在の行数を状態ファイルに保存して次回のチェックに備える。

    ※「パストラーバーサル」や「Dos対策」の懸念が考えられるが、このPythonスクリプトが機能するのは Antigravity CLI であり、「`transcript_path`（会話履歴ログ）や`state_file_name`（会話履歴ログの行数管理ファイル）は、システム自身の内部ロジックで生成・指定される固定的なパス」でしか機能しない。つまり、「ローカル完結型のツール」なため無視できると判断した。
    """

    if not transcript_path or not os.path.exists(transcript_path):
        return False

    # 自身のスクリプトがあるディレクトリ（`.agents/hooks/`）を取得する
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # プロジェクトルートディレクトリを取得（`.agents/hooks/`の2階層上）
    project_root = os.path.dirname(os.path.dirname(base_dir))
    # （プロジェクトルートにある）tasks ディレクトリのパスを構築
    tasks_dir = os.path.join(project_root, "tasks")
    # tasks ディレクトリが存在しない場合は作成する
    os.makedirs(tasks_dir, exist_ok=True)
    # 直前の実行時のトランスクリプトの行数を保存した状態ファイルを指定する
    state_file = os.path.join(tasks_dir, state_file_name)

    # 初回推論時は状態ファイルを初期化（0行に上書き保存）する
    if is_first_invocation:
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                f.write("0")
        except Exception as e:
            sys.stderr.write(f"Error initializing state file: {e}\n")

    last_line_count = 0
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                # 直前の実行時のトランスクリプトの行数を格納（確実に数値型として扱う）
                last_line_count = int(f.read().strip())
        except Exception as e:
            sys.stderr.write(f"Error reading state file: {e}\n")

    # コンテキストの自動圧縮が発生したかどうかを判定するフラグ
    checkpoint_detected = False
    current_line_count = 0  # 会話ログファイルの現在の行数

    try:
        # 会話ログファイル（`transcript_path`）を読み込む
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                current_line_count += 1
                # まだコンテキストの自動圧縮が発生していない場合、かつ現在の行数が前回のチェック時より大きい（会話ログが更新されている）場合
                if not checkpoint_detected and current_line_count > last_line_count:
                    try:
                        # 各行をJSONとしてパース（後続の抽出処理をスムーズに進めるため）
                        log_entry = json.loads(line)
                        # "source"が"SYSTEM"かつ"type"が"CHECKPOINT"であるかを判定
                        if (
                            log_entry.get("source") == "SYSTEM"
                            and log_entry.get("type") == "CHECKPOINT"
                        ):
                            content = log_entry.get("content", "")  # ログの中身

                            # `CHECKPOINT`が 0 じゃない（0以上の）場合にコンテキストの自動圧縮を検知
                            if "{{ CHECKPOINT 0 }}" not in content:
                                checkpoint_detected = True
                    except json.JSONDecodeError:
                        pass

    except Exception as e:
        sys.stderr.write(f"Error reading transcript: {e}\n")

    # 既にセッションが開始されている場合（会話ログが1行以上ある場合）
    if current_line_count > 0:
        try:
            dir_name = os.path.dirname(state_file)
            # 状態ファイル（`state_file`）へ現在のログ行数を書き込む
            with tempfile.NamedTemporaryFile(
                "w", dir=dir_name, delete=False, encoding="utf-8"
            ) as tf:
                # 処理の完了保証のため一時ファイルのパスを書き込み前に取得する（リソースリーク対策）
                temp_name = tf.name
                tf.write(str(current_line_count))

            # 一時ファイルから正式な状態ファイルへアトミック（処理の完了保証）に置き換える
            os.replace(temp_name, state_file)
        except Exception as e:
            sys.stderr.write(f"Error writing state file: {e}\n")
            if "temp_name" in locals() and os.path.exists(temp_name):
                try:
                    # 一時ファイルの削除
                    os.remove(temp_name)
                except OSError:
                    pass

    return checkpoint_detected


def check_invocation_num(input_data, invocation_num=0):
    """
    当該呼び出し回数かどうかを判定するPythonスクリプト。`input_data`（json形式のシステムフックペイロードをパースした内容）と、`invocation_num`（判定したい呼び出し回数。※デフォルト値は0）を受け取って「当該呼び出し回数かどうかを判定」する。
    """

    # stepIdx（会話履歴のターン数）を取得
    step_idx = input_data.get("stepIdx")

    if step_idx is None:
        # stepIdx がなければ invocationNum（エージェントの呼び出し回数）にフォールバック、なければ 0 を指定
        step_idx = input_data.get("invocationNum", 0)

    try:
        # 確実に数値型として扱い、比較する（文字列の "0" などへの対応）
        is_target_invocation = int(step_idx) == invocation_num
    except Exception:
        is_target_invocation = False

    return is_target_invocation
