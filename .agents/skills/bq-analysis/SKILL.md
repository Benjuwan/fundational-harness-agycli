---
name: bq-analysis
description: 自然言語の指示から BigQuery 用の SQL を自動構築し、GA4 データの抽出・集計・分析を安全かつ厳格なコスト・セキュリティガードレールのもとで実行するスキル。ユーザーから「GA4のデータを分析して」「BigQueryでPV数やセッション数を調べて」「/bq-analysis」などの指示があった時に使用します。
---

## bq-analysis (BigQuery × GA4 自然言語分析スキル) 概要
ユーザーからの日本語指示を解析し、GA4（Google アナリティクス 4）の BigQuery エクスポートデータに対する安全で最適な SQL（Standard SQL）を生成・事前検証・実行・集計するスキルです。

<instructions>

## ワークフロー (処理シーケンス)

### Step 1: 初期化・設定参照 ＆ バリデーション
1. `tasks/tmp/` ディレクトリが存在しない場合は作成（`mkdir -p tasks/tmp/`）します。
2. `tasks/tmp/bq_analysis_config.json` の存在を確認します。
   - 存在しない場合（初回）: ユーザーに以下のフォーマットで情報入力を促し、入力された情報を `tasks/tmp/bq_analysis_config.json` に保存します（デフォルト安全閾値 `max_scan_gb_threshold: 3.0` を含む）。
```
以下、GA4データと連携しているBigQueryプロジェクト情報および、分析・解析対象のGA4情報を入力してください。

- **GCP Project ID（プロジェクトID）**: （例: `intricate-aria-123456-j123`）
- **Dataset ID（データセットID）**: GA4のプロパティID（例: `analytics_123456789`）
- **Location（リージョン）**: （例: `US` や `asia-northeast2`）, `asia-northeast2`は大阪リージョン、`asia-northeast1`は東京リージョンです
```
   - 存在する場合: 保存された設定（`project_id`, `dataset_id`, `location`, `max_scan_gb_threshold`）を読み込みます。
3. **変数サニタイズ ＆ 自動補完（コマンドインジェクション防止・UX向上）**:
   - `location`: 半角英数字およびハイフンのみ許可（例: `asia-northeast2`）。
   - `project_id`: 半角英数字、ハイフン、ドットのみ許可。
   - `dataset_id`: 半角英数字およびアンダースコアのみ許可。
     - **自動補完ルール**: ユーザー入力の `dataset_id` が数字のみ（例: `123456789`）の場合、または先頭に `analytics_` が付いていない場合は、自動的に頭に `analytics_` を付与して `analytics_123456789` として整形・保存・読み込みを行います（すでに `analytics_` で始まる場合はそのまま保持）。
   - 不正な文字が含まれている場合は即時処理を停止し、再設定を要求します。
4. 接続疎通テストを実行します:
   ```bash
   bq query --use_legacy_sql=false --dry_run --location=<LOCATION> 'SELECT 1'
   ```

### Step 2: 自然言語解析 ＆ ガードレール付き SQL 生成
ユーザー指示から要求意図（集計期間、指標、軸）を抽出し、以下の**厳格な安全ガードレール**を適用した SQL を生成します。

#### セキュリティ・コスト ガードレールルール
1. **READ-ONLY（単一ステートメント）の強制**:
   - `SELECT` または `WITH ... SELECT` で始まる単一クエリのみを許可。
   - **セミコロン（`;`）を含めることを禁止**（マルチステートメントバイパス防止）。
   - DML/DDL キーワード（`\bDROP\b`, `\bDELETE\b`, `\bUPDATE\b`, `\bINSERT\b`, `\bMERGE\b`, `\bCREATE\b`, `\bALTER\b`, `\bTRUNCATE\b`, `\bGRANT\b`, `\bREVOKE\b` 等）が**大文字・小文字を区別せず（Case-Insensitive）**独立単語として含まれる場合は**絶対に実行せず拒否**する（※単語境界 `\b` を考慮し `updated_at` 等のカラム名誤検知を防止）。
2. **SQLコメント（`--`, `/* */`, `#`）の禁止**:
   - ガードレール回避バイパス（条件無効化など）を防ぐため、生成する SQL にいかなるコメント（`--`, `/* */`, `#`）を含めることも禁止する。
3. **`SELECT *` の禁止**: カラムは必要なもの（例: `event_date`, `event_name` 等）のみ明示的に指定。
4. **`_TABLE_SUFFIX` 日付フィルターの自動強制 ＆ 存在チェック**:
   - 期間の指定がない場合、自動的に過去 7 日間（`_TABLE_SUFFIX BETWEEN 'YYYYMMDD' AND 'YYYYMMDD'`）を追加。
   - 日付文字列はハイフンなし 8 桁（`'YYYYMMDD'`）。
   - **クエリ内に `_TABLE_SUFFIX` 条件が含まれていない場合は、全テーブルスキャン防止のためドライランを実行せず即時拒否・再生成する**。
   - ※`OR` 条件指定時も全体に `_TABLE_SUFFIX` が効くよう、かっこ等で論理優先順位を正しく保護する。
5. **`intraday` テーブルの除外**:
   - 重複カウント防止のため `WHERE _TABLE_SUFFIX NOT LIKE '%intraday%'` 条件を必須で追加。

### Step 3: クエリ安全保存 ＆ Dry-Run（JSONパース ＆ フェイルセーフ）
1. シェルインジェクション防止のため、生成した SQL を一度 `tasks/tmp/query.sql` に書き出します。
2. `--dry_run` および `--format=json` で事前検証を実行します:
   ```bash
   bq query --use_legacy_sql=false --dry_run --format=json --location=<LOCATION> < tasks/tmp/query.sql
   ```
3. **Python スクリプトによる見積もりバイト数の安全パース**:
   - 実行結果の JSON から `totalBytesProcessed` を Python でパースします。
   - **パース失敗（フェイルセーフ）**: JSONパースエラーや値が取得できない場合は、スキャン量を「不明（高リスク）」と判定し、自動実行せずに必ずユーザーにエラー内容と確認を求めます。
4. **構文エラー時の自動リカバリ ＆ ガードレール再適用**:
   - 構文エラーが発生した場合、エラー内容を解析して最大 2 回まで SQL を修正し、`tasks/tmp/query.sql` に上書きして試行します。
   - **重要**: 自動修正した SQL についても、必ず **Step 2 のセキュリティガードレール（`_TABLE_SUFFIX`の存在、DML/コメント禁止など）を再検証** してから Dry-Run を行います。
   - **2 回修正しても解消しない場合**: 独断で処理を続けず、エラー全文と `tasks/tmp/query.sql` の内容をユーザーに提示し指示を仰ぎます。

### Step 4: スキャン上限判定 ＆ 事前承認 (HITL)
1. 取得したスキャンバイト数から GB（Bytes ÷ 1024^3）を計算します。
2. ユーザーに対し、以下を明示して実行承認（`y/n`）を求めます（`hitl-policy.md` 準拠）:
   - 生成された SQL の要約 / `tasks/tmp/query.sql` への参照
   - 見積もりスキャンデータ量（例: 「約 0.25 GB」または「約 12.5 GB」）
   - 設定された安全閾値（`max_scan_gb_threshold`: デフォルト 3.0 GB）
3. **承認判定**:
   - 見積もりが閾値（3.0 GB）を超える場合は、高スキャン量リスクに関する明確な注意文を提示し事前承認（`y/n`）を得ます。
   - 閾値以下の場合も、本実行前に簡潔な確認（`y/n`）を行います。
4. ユーザーが承認（`y`）した場合、承認された見積もりスキャン量バイト数に 20% の安全マージンを加算した値（`int(estimated_bytes * 1.2)`）と設定閾値バイト数のうち、**小さい方の値**を決定します。
   - **※BigQuery物理制限（10 MB下限ガード）**: BigQueryの仕様上 `--maximum_bytes_billed` オプションには 10 MB（`10485760` Bytes）以上を指定する必要があるため、上記で決定された値が `10485760` 未満の場合は **`10485760`（10 MB）** を物理上限バイト数（`APPROVED_MAX_BYTES`）として決定します。
   - **※セーフティ設計の意図**: ユーザーが閾値を超える見積もりを承認した場合であっても、AIの暴走やヒューマンエラーによる課金過多を物理的に防ぐため、設定閾値（デフォルト3.0GB）を超える上限はシステムとして許容しません。

### Step 5: クエリ実行 ＆ 物理上限付与 ＆ PythonによるCSV保存 ＆ 要約提示
1. 万が一の過剰課金を物理的に遮断するため、決定した `APPROVED_MAX_BYTES` を `--maximum_bytes_billed` オプションに指定し、JSON フォーマットでクエリを実行します（コンテキスト溢れ防止のため `--max_rows=100` を付与）:
   ```bash
   bq query --use_legacy_sql=false --maximum_bytes_billed=<APPROVED_MAX_BYTES> --max_rows=100 --format=prettyjson --location=<LOCATION> < tasks/tmp/query.sql > tasks/tmp/bq_result.json
   ```
2. **Python スクリプトによる CSV 変換・保存**:
   - 取得した JSON 結果 (`tasks/tmp/bq_result.json`) を Python スクリプトで変換し、`tasks/tmp/ga4_analysis_output.csv` に正確に書き出します。
   - シェルエスケープ事故を防ぐため、一時スクリプト `tasks/tmp/convert_json.py` を作成して実行します（※Windows環境では`python3`ではなく`python`で実行）。
   ```bash
   cat << 'EOF' > tasks/tmp/convert_json.py
   import json, csv, sys
   try:
       with open('tasks/tmp/bq_result.json', 'r', encoding='utf-8') as f:
           data = json.load(f)
       if data and isinstance(data, list):
           keys = data[0].keys()
           with open('tasks/tmp/ga4_analysis_output.csv', 'w', newline='', encoding='utf-8') as f_out:
               writer = csv.DictWriter(f_out, fieldnames=keys)
               writer.writeheader()
               writer.writerows(data)
   except Exception as e:
       print(f"JSONパースエラー: クエリ結果が正しくないか、エラーが発生しています。({e})")
       sys.exit(1)
   EOF
   python3 tasks/tmp/convert_json.py
   ```
3. ユーザーの対話画面には以下を出力します:
   - TOP 10〜20 件の要約マークダウンテーブル
   - 分析インサイト（結果に対する考察・アドバイス）
   - 保存された CSV ファイルへのハイパーリンク（例: [`[YYYYMMDD_]ga4_analysis_output.csv`](tasks/tmp/ga4_analysis_output.csv)）

## 参照ドキュメント
詳細な GA4 スキーマ、`UNNEST` クエリ例、IAM 権限、Python 変換スクリプト詳細は [bq-analysis-reference.md](references/bq-analysis-reference.md) を参照してください。

</instructions>
