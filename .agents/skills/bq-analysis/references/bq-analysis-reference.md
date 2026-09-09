# BigQuery × GA4 自然言語分析スキル（bq-analysis）実装・運用ガイド
本ドキュメントは、自然言語（日本語）の指示から BigQuery 用の SQL を自動的に作成し、GA4（Google アナリティクス 4）のデータを抽出・解析する Skill（カスタムツール）を導入・運用するための完全ガイドです。  
非エンジニアやナレッジワーカーの方でも理解・設定できるよう、専門用語の解説からツール（Google Cloud CLI）のインストール手順、IAM 権限の設定、SQLパターン、コスト・セキュリティ防止策までをステップバイステップで解説します。

## 用語の整理（まずここから）

- **BigQuery（ビッグクエリ）**: Google が提供する超高速なデータ分析用データベース。GA4 の詳細なデータを蓄積できます。
- **GA4 BigQuery エクスポート**: GA4 で計測されたユーザーの行動ログ（ページ閲覧やクリック等）を、生のまま BigQuery へ自動転送する仕組み。
- **GCP Project ID（プロジェクトID）**: Google Cloud 上で自社システムやデータを管理する全体の識別番号（例: `my-company-analytics`）。
- **Dataset ID（データセットID）**: BigQuery 内で GA4 データが格納されているフォルダ名（例: `analytics_123456789`）。
  - **データセットIDの確認場所**: データセットIDの数字部分（`123456789`）は、GA4の「プロパティID」と同じです。Google アナリティクス 4 の [管理] ＞ [プロパティ] ＞ [`プロパティの詳細`（画面右上付近）] から確認できます。
  - **Dataset ID の自動補完**: ユーザー入力が数字のみ（GA4プロパティID）の場合、本スキルが自動的に頭に `analytics_` を補完してデータセットID（`analytics_123456789`）を生成・補正します。
- **Location（リージョン）**: データが保管されている地理的場所（例: `US`, `asia-northeast1`）。
- **SQL（エスキューエル）**: データベースから欲しいデータを取り出すための命令文。
- **gcloud / bq CLI**: パソコンのターミナル（黒い画面）から Google Cloud を操作するための公式ツール。

## 1. 準備ステップ：ツールのインストールとログイン設定
Skill から BigQuery へアクセスできるようにするために、パソコンへの「Google Cloud CLI（`bq` コマンド）」の準備を行います。

### ステップ 1-1: Google Cloud CLI のインストール
`bq` コマンドを使うには、Google 公式の[「Google Cloud SDK（CLI）」をインストール](https://docs.cloud.google.com/sdk/docs/install-sdk?hl=ja)します。

> [!NOTE]
> Google Cloud SDK（CLI）が既にあるかどうかを確認するには以下のコマンドを使用  
> `gcloud version`または`gcloud --version`.
> `command not found: gcloud`などのエラーが表示された場合はインストールされていないのでインストールしてください。

#### macOS の場合
1. ターミナルを開き、以下のコマンド（Homebrewを利用）を実行します：
   ```bash
   brew install --cask google-cloud-sdk
   ```
2. （Homebrewが無い場合）Google 公式サイトから macOS 用インストーラ（`.tar.gz`）をダウンロードして解凍し、付属の `install.sh` を実行します。
   - [Google Cloud CLI インストール公式ページ（macOS）](https://cloud.google.com/sdk/docs/install?hl=ja#mac)

#### Windows の場合
1. Google 公式サイトから「Google Cloud CLI インストーラー (`GoogleCloudSDKInstaller.exe`)」をダウンロードして実行します。
   - [Google Cloud CLI インストーラー（Windows）](https://cloud.google.com/sdk/docs/install?hl=ja#windows)
2. 画面の指示に従いインストールを完了させます（`bq` コマンドの自動パス設定が含まれます）。

### ステップ 1-2: ログインと初期設定
インストールが完了したら、ターミナル（またはコマンドプロンプト）で以下のコマンドを実行し、Google アカウントでログインします。

1. **Google アカウントにログイン**
   ```bash
   gcloud auth login
   ```
   - コマンドを実行するとブラウザが開きます。BigQuery へのアクセス権がある Google アカウントを選択して「許可」をクリックします。

2. **デフォルトのプロジェクト ID を設定**
   ```bash
   gcloud config set project <あなたのGCPプロジェクトID>
   ```
   - プロジェクトIDは [Google Cloud Console](https://console.cloud.google.com/) 画面上部の「プロジェクト選択」から「ID」列で確認できます（プロジェクト名とは異なる場合があります）。

3. **動作確認（疎通テスト）**
   以下のコマンドを実行し、エラーが出ずに結果が返ってくれば（例: `Query successfully validated...`）準備完了です（※リージョンが大阪の場合は `--location=asia-northeast2` を指定）
   ```bash
   bq query --use_legacy_sql=false --dry_run --location=US 'SELECT 1'
   ```

> [!NOTE]
> - **イレギュラー対応（クォータ警告が出た場合）**  
> 「2. デフォルトのプロジェクト ID を設定」を実行した際に、`WARNING: Your active project does not match the quota project...` という警告が出ることがあります。これはAPI利用枠（クォータ）の対象プロジェクトがズレていることが原因です。  
> 警告が出た場合、またはAIアシスタント経由で分析を行う場合は、続けて `gcloud auth application-default login` コマンドを実行し、ブラウザで再度「許可」を行って認証情報を更新（ADCを設定）してください。 
> 
> - **アカウント情報の確認コマンド**  
> 認証済みアカウント一覧と現在アクティブなものの確認: `gcloud auth list`  
> プロジェクトIDやリージョンなど現在の設定全体の確認: `gcloud config list`

## 2. Google Cloud の権限（IAM）設定

> [!WARNING]
> **※注意：GA4の権限とBigQueryの権限は別物です**
> ここで必要なのは、GA4の管理画面の権限ではなく、裏側のデータベース（BigQuery）へアクセスするための「GCP（IAM）の権限」です。他社や別アカウントのデータを分析したい場合は、GA4の管理者ではなく「GCPの管理者」へ以下の依頼を行ってください。

他社や別部門が管理するGA4のデータを分析する場合、事前に以下の2点を確認・対応する必要があります。

### 事前確認1: GA4のBigQueryエクスポート設定が完了しているか
GA4のデータがそもそもBigQueryに連携（エクスポート）されていないと分析できません。

- **【確認方法】**
1. 対象のGA4プロパティの管理画面（左下の歯車アイコン）を開きます。
2. 「`サービス間のリンク設定`」セクションにある「`BigQueryのリンク`」をクリックします。
3. リンク一覧にプロジェクトが表示されていれば連携されています。この時表示されているプロジェクトIDが、後でGCP管理者に権限を依頼する対象のプロジェクトとなります。

### 事前確認2: 誰がGCP（Google Cloud）の管理者か
対象プロジェクトのBigQueryにアクセスするには、そのプロジェクトのGCP管理者にあなたのGoogleアカウントを登録してもらう必要があります。

- **【確認方法】**  
GCPの管理者は、自社の情シス（社内SE）部門やインフラエンジニア、またはWebサイトのインフラを構築した外部ベンダーであることが多いです。関係者に「このGA4が連携しているGCPプロジェクトの管理者は誰か」を確認してください。
管理者が判明したら、以下のアクセス権限（IAM ロール）を付与してもらうよう依頼します。

### 必要なアクセス権限（2つだけ）
BigQuery 内のデータを参照し、分析クエリを実行するために以下の2つの役割（ロール）が必要です。

1. **BigQuery データ閲覧者 (`roles/bigquery.dataViewer`)**
   - 用途: GA4 データセット内のテーブル（イベントログ）を読み取る権限。
2. **BigQuery ジョブユーザー (`roles/bigquery.jobUser`)**
   - 用途: クエリ（検索ジョブ）を発行・実行し、結果を取得する権限。

> [!NOTE]
> - **自身の権限確認方法**  
> [Google Cloud Console](https://console.cloud.google.com/) の「`IAM と管理`」>「`IAM`」画面で自分のアカウントに上記ロールがあるか確認する。上記、必要なアクセス権限がない場合は、GCP管理者に権限を付与してもらうよう依頼する（以下参照）。

---

> [!WARNING]
> - **「My First Project」など自身が管理者であるプロジェクトの注意点**  
> 自動生成される「My First Project」など自分がオーナーのプロジェクトであれば、自身で自由に権限を付与できます。  
> ただし、そこで分析を行うには **「対象のGA4の管理画面から、そのプロジェクトに対してBigQueryエクスポート（リンク設定）が行われていること（事前確認1の内容）」** が必須です。GA4のデータが別のプロジェクトに連携されている場合は、いくら自身のプロジェクトで権限を設定してもデータは参照できないため、正しい連携先プロジェクトの管理者に依頼を行ってください。

---

> **管理者への依頼文テンプレート**:  
> 「GA4 の BigQuery データを AI アシスタント経由で分析するため、対象の GCP プロジェクトにて私の Google アカウント（またはサービスアカウント）に `BigQuery データ閲覧者` と `BigQuery ジョブユーザー` の権限付与をお願いします」

#### 【管理者向け】権限の付与手順
依頼を受けた管理者は、以下の手順で対象者に権限を付与してください。
1. [Google Cloud Console](https://console.cloud.google.com/) の「`IAM と管理`」>「`IAM`」を開きます。
   - ※デフォルトでは画面上部にある「`許可`タブ」が選択状態になっていて、その隣りにある「`許可しない`（Deny）タブ」を選択すると拒否ポリシー（※参照記事: [BigQuery × AI で 300 万円溶かそう](https://qiita.com/na0/items/e7eb24f896749fd3f190) に記載ある*CREATE CAPACITY は IAM 拒否ポリシーで `bigquery.capacityCommitments.create` 権限を拒否*する）設定が行える。ただし拒否ポリシー設定の権限（`iam.denypolicies.create`）がない場合もあるので注意。
2. 「`アクセスを許可`」をクリックし、設定画面を表示します。
3. 表示された設定画面で、「新しいプリンシパル」に依頼者のメールアドレスを入力します。
4. 「`ロール`」から **`BigQuery データ閲覧者`** と **`BigQuery ジョブユーザー`** の2つのロールを選択し、「`保存`」をクリックします。

> [!NOTE]
> ##### 拒否ポリシーの設定フロー事例（※`bigquery.capacityCommitments.create`の設定例）
> **事前準備**: 上記1の通り、設定には `iam.denypolicies.create` の権限が必要です。作業者のアカウントにこの権限を含む「拒否管理者（`roles/iam.denyAdmin`）」ロールが付与されていることを確認してください（プロジェクトのオーナー権限だけでは作成できません）。
> 
> 1. IAM画面上部の **[拒否]**（またはDeny）タブを選択し、**[＋ 拒否ポリシーを作成]** をクリックします。
> 2. **「ポリシー名」** を設定します。
>    - 表示名: 任意のわかりやすい名前（例: `BigQueryスロット購入制限`）
>    - ID: 任意の英数字ハイフン（例: `prevent-bq-commitments`）※後から変更不可
> 3. **「新しい拒否ルール」** セクションで以下を入力します。
>    - **プリンシパルの追加（拒否されたプリンシパル）**: （例）プロジェクト全員を対象とする場合は `principalSet://goog/public:all`
>    - **権限の追加（拒否された権限 / 権限 1）**: ブロックする API 権限を指定します（大抵サジェストで候補が出てくる）。（例） `bigquery.googleapis.com/capacityCommitments.create`
> 4. 枠内右下の **[完了]** をクリックし、画面下部の **[作成]** をクリックするとポリシーが適用されます（反映まで数分かかる場合があります）。

#### 任意のメールアドレスにアクセス権を付与・管理する際の仕様と前提条件
Google Cloud のプロジェクトに対して、`IAM（Identity and Access Management）`機能を利用し、任意のメールアドレスにアクセス権を付与・管理する際の仕様と前提条件は以下になります。

##### 1. 任意のメールアドレスに対するアクセス管理
プロジェクトの「オーナー」または「IAM 管理者」権限を持つユーザーは、IAM設定画面から以下の操作を柔軟かつ一元的に行うことが可能です。

- Gmail以外のメールアドレスへの付与:  独自ドメイン（会社のメールアドレスなど）を含む、任意のメールアドレスを「プリンシパル（その権限をもらって何かをする側/処理実行者）」として指定し、アクセス権を付与することができます。
- 役割に応じた適切な権限（ロール）の割り当て:  プロジェクト全体の操作権限を与えるだけでなく、「BigQueryのデータ閲覧・操作のみ」といった、目的に応じた特定の機能（ロール）だけをピンポイントで付与できます。
- アクセス権のコントロール:  作業が必要なタイミングでアクセス権を許可し、不要になったら速やかにアクセス権を削除するといった管理が可能です。

> [!WARNING]
> - 【重要】対象メールアドレスの前提条件  
> 任意のメールアドレスに権限を付与し、実際に Google Cloud の機能を利用させるためには、**Google アカウントとしての登録・連携が必須（※1）**となります。Google Cloud を利用する際にログイン認証を行うため単なるメールアドレスではなく、Googleの認証基盤を通れる状態になっている必要があるためです。  
> ※1: 追加するメールアドレスが、Google アカウント（または Google Workspace / Cloud Identity アカウント）として事前に作成・紐付けられている状態

##### 2. 権限範囲に関する注意点（Google Cloudと連携元サービスの違い）
Google Cloud 側で権限を付与したからといって、データ連携元サービスのアクセス権まで付与されるわけではありません。これらは分けて管理する必要があります。

- Google Cloudの権限で「できること」:  （例）IAM で「BigQuery ユーザー」のロールを付与した場合、対象者は Google Cloud（BigQuery）にログインし、蓄積されたデータを直接操作・分析できます。
- Google Cloud の権限では「できないこと」:  （例）Google Cloud 側で権限を与えても、データ連携元である GA4 自体の管理画面や標準レポート画面を閲覧できるようにはなりません。GA4側の閲覧・操作もさせたい場合は、別途GA4の管理画面からユーザー追加を行う必要があります。  
※詳細は[事前確認1: GA4のBigQueryエクスポート設定が完了しているか](#事前確認1-ga4のbigqueryエクスポート設定が完了しているか)を参照してください。

## 3. スキルの起動と分析の実行フロー
必要な権限設定が完了したらAIアシスタントにデータ分析を依頼できます。本スキルは以下のフローで進行します。

### 1. スキルの呼び出しと初回設定
- `agy`で起動したTUI画面で「GA4のデータを分析して」や「`/bq-analysis`」と入力してスキルを起動します。
- 初回起動時のみ、AIから以下の3つの情報の入力を求められます。
  - **GCP Project ID（プロジェクトID）**: （例: `intricate-aria-123456-j123`）
  - **Dataset ID（データセットID）**: GA4のプロパティID（例: `analytics_123456789`）
  - **Location（リージョン）**: （例: `US` や `asia-northeast2`）
- 一度入力すると設定ファイル（`tasks/tmp/bq_analysis_config.json`）に保存され、次回からは聞かれません。

### 2. 自然言語による分析指示
- 「先月のPV数を日別に出して」「昨日のスマートフォンからのセッション数は？」など、普通の日本語で知りたいデータをお願いします。
- AIがあなたの指示を解釈し、BigQuery 用の SQL を自動的に作成します。

### 3. 事前見積もりと承認（HITL）
- AI はすぐにはクエリを実行しません。まずは「Dry-Run（空振りテスト）」を行い、**「どのくらいのデータ量をスキャンするか（＝いくらコストがかかりそうか）」** を計算してチャットに提示します。
- 提示されたスキャン量（例: `約 0.25 GB` など）とSQLの要約を確認し、問題なければ **「y」や「はい」** と返答して実行を承認してください。
- ※もしスキャン量が異常に多い場合や、想定と違う場合は「n（いいえ）」と答えて指示をやり直せます。

### 4. 分析結果の受け取り
- 承認後、AIが安全にクエリを実行します。
- チャット画面に**上位の結果（表形式）** と **データの考察（インサイト）** が提示されます。
- さらに、すべての結果データは CSV ファイル（`tasks/tmp/ga4_analysis_output.csv`）として保存され、チャットからダウンロード可能なリンクが提供されます。

## 4. GA4 のデータ構造と標準 SQL パターン

> [!NOTE]
> **これ以降の章（第4章〜第7章）は、主にAIアシスタントが安全かつ正確にSQLを生成・実行するための技術的仕様およびリファレンスです。**  
> ユーザーが直接 SQL を書いたり、これらの制約を暗記・操作する必要はありません。AIが参照する内容です。

---

GA4 のデータは、1行の中に複数の情報（イベント名、パラメータ、ユーザー属性など）が入れ子構造（ネスト）になって保存されています。AI はこの構造を理解して SQL を自動生成します。

### GA4 テーブルの基本構造
- **テーブル名ルール**: `<PROJECT_ID>.<DATASET_ID>.events_YYYYMMDD`
  - **`DATASET_ID`の自動補完ルール**: ユーザー入力の `DATASET_ID` が数字のみ（例: `123456789`）の場合、または先頭に `analytics_` が付いていない場合は、自動的に頭に `analytics_` を付与して `analytics_123456789` として整形・保存・読み込みを行います（すでに `analytics_` で始まる場合はそのまま保持）。
- **日付フィルターの超重要ルール**:  
  `_TABLE_SUFFIX` は **ハイフンなしの8桁文字列（`'YYYYMMDD'`）** で指定します。  
  ❌ 間違い: `'2026-07-01'`  
  ⭕ 正しい: `'20260701'`  
- **リアルタイムテーブルの除外**:  
  GA4 には当日の速報用 `events_intraday_*` テーブルが存在するため、重複カウントを防ぐ目的で必ず `AND _TABLE_SUFFIX NOT LIKE '%intraday%'` 条件を付与します。

### 代表的な分析 SQL パターン

#### ① 日別 PV（ページビュー）数の集計
```sql
SELECT
  event_date,
  COUNT(1) AS page_views
FROM
  `<PROJECT_ID>.<DATASET_ID>.events_*`
WHERE
  event_name = 'page_view'
  AND _TABLE_SUFFIX BETWEEN '20260701' AND '20260731' -- シングルクォート付き8桁
  AND _TABLE_SUFFIX NOT LIKE '%intraday%'           -- intraday除外
GROUP BY
  event_date
ORDER BY
  event_date ASC;
```

#### ② セッション数（`ga_session_id`）の正確なカウント
```sql
SELECT
  COUNT(DISTINCT CONCAT(user_pseudo_id, CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING))) AS sessions
FROM
  `<PROJECT_ID>.<DATASET_ID>.events_*`
WHERE
  _TABLE_SUFFIX BETWEEN '20260701' AND '20260731'
  AND _TABLE_SUFFIX NOT LIKE '%intraday%';
```

#### ③ ページURL（`page_location`）別の閲覧数ランキング
```sql
SELECT
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page_location,
  COUNT(1) AS pv_count
FROM
  `<PROJECT_ID>.<DATASET_ID>.events_*`
WHERE
  event_name = 'page_view'
  AND _TABLE_SUFFIX BETWEEN '20260701' AND '20260731'
  AND _TABLE_SUFFIX NOT LIKE '%intraday%'
GROUP BY
  page_location
ORDER BY
  pv_count DESC
LIMIT 20;
```

## 5. コスト・安全性管理（ガードレール設計）
> **※以下は、AIアシスタントが裏側で自動的に行う安全対策の仕様です（ユーザー側の設定は不要です）**

GA4 のデータは膨大なため、予期せぬ課金やセキュリティ事故を防ぐ安全ルールを Skill 側に組み込みます。

1. **厳格な READ-ONLY（単一ステートメント）制限**
   - 生成される SQL は単一の `SELECT` または `WITH ... SELECT` で始まるクエリのみを許可します。
   - **マルチステートメントの禁止**: セミコロン（`;`）による複数クエリの結合はバイパス対策のため一切禁止します。
   - **DML/DDL の自動却下（単語境界チェック）**: 大文字・小文字を区別せず（Case-Insensitive）、単語境界（`\b`）を考慮し、`\bDROP\b`, `\bDELETE\b`, `\bUPDATE\b`, `\bINSERT\b`, `\bMERGE\b`, `\bCREATE\b`, `\bALTER\b`, `\bTRUNCATE\b`, `\bGRANT\b`, `\bREVOKE\b` 等が含まれる場合は自動的に実行を却下します（※`updated_at` 等のカラム名・リテラルとの誤検知を防止）。
   - **`AI.` / `ML.` 名前空間関数・`EXTERNAL_QUERY` の自動却下**: DML/DDL チェックをすり抜けて外部モデル・APIを行単位で呼び出します。課金は BigQuery のバイト課金とは別建てで外部サービスから直接請求されるため、Dry-Run にも `--maximum_bytes_billed` にも現れません。本項の判定は大小文字を無視し、空白（改行・タブ含む）とバッククォートを除去したうえで `(AI|ML)\.[A-Za-z_]+\(` / `EXTERNAL_QUERY\(` に一致したら却下します。**単語境界 `\b` は付けません**（空白除去で直前トークンと連結するため `\b` を課すと全て素通りし、逆に `\(` を省くと `openai.com` 等を誤拒否します）。
2. **SQLコメント（`--`, `/* */`, `#`）の全面禁止**
   - ガードレール判定（`_TABLE_SUFFIX` の有無や DML キーワードのチェック）をコメントアウトで回避するバイパス攻撃を防ぐため、生成クエリ内での SQL コメント（`--`, `/* */`, `#`）の利用を完全に禁止します。
3. **シェルインジェクション防止（ファイル経由実行 ＆ 変数サニタイズ）**
   - 生成された SQL を直接コマンドライン引数に渡すとシェル文字（`;`, `$()`, ``` `` ``` 等）によるインジェクションリスクが発生するため、必ず一度 `tasks/tmp/query.sql` に安全に書き出し、`bq query --use_legacy_sql=false < tasks/tmp/query.sql` で実行します。
   - コマンド引数に含まれる `<LOCATION>` や `<PROJECT_ID>` などの変数も半角英数字・ハイフンに制限・サニタイズします。
4. **日付フィルター（`_TABLE_SUFFIX`）の自動強制 ＆ 存在チェック**
   - 期間の指定がない指示の場合、自動的に「過去 7 日間」等のフィルターを追加します。
   - **事前チェック**: 生成された SQL に `_TABLE_SUFFIX` 条件が存在しない場合は、全テーブルスキャンを防ぐためドライランを行わず即時拒否・再生成します。
5. **JSON フォーマットによる Dry-Run ＆ Python による安全パース**
   - クエリ実行前に `--dry_run --format=json` を行い、SQL の構文チェックと見積もりスキャンデータ量（Byte）の計算を実施します。
   - **Python パースロジック**:
     Dry-Run の JSON 結果から Python で `totalBytesProcessed` を抽出し、GB 換算（`Bytes / 1024^3`）します。
     ```python
     import json
     try:
         data = json.loads(json_output)
         total_bytes = int(data['statistics']['query']['totalBytesProcessed'])
     except Exception:
         total_bytes = None  # パース失敗時は安全側に倒して「スキャン量不明」として確認を求める
     ```
6. **動的承認値に基づく `--maximum_bytes_billed` の物理遮断**
   - **スキャンバイト課金にのみ作用**（AI/ML・外部API課金には無効）。万が一ドライランの判定漏れが発生した場合でも BigQuery 側で物理的に超過課金を防ぐため、承認された見積もりスキャンサイズに 20% の安全マージンを加算した値（`int(estimated_bytes * 1.2)`）と設定上限値のうち**小さい方の値**を物理上限バイト数 (`APPROVED_MAX_BYTES`) として決定し、`--maximum_bytes_billed=<APPROVED_MAX_BYTES>` で強制付与します。
7. **Python による JSON 結果の CSV 安全変換**
   - ターミナルでのフォーマット不整合（JSON と CSV 拡張子の矛盾）を解消するため、`bq query --format=prettyjson` の結果を JSON ファイルに保存後、Python スクリプトにて CSV ファイル（`tasks/tmp/ga4_analysis_output.csv`）へ変換・保存します。
   ```python
   import csv, json
   with open('tasks/tmp/bq_result.json', 'r', encoding='utf-8') as f:
       data = json.load(f)
   if data and isinstance(data, list):
       keys = data[0].keys()
       with open('tasks/tmp/ga4_analysis_output.csv', 'w', newline='', encoding='utf-8') as f_out:
           writer = csv.DictWriter(f_out, fieldnames=keys)
           writer.writeheader()
           writer.writerows(data)
   ```

## 6. 設定情報のローカル保持（設定ファイルの利用）
初回に入力した `GCP Project ID`, `Dataset ID`, `Location` は、`tasks/tmp/bq_analysis_config.json` にローカル保存され、次回以降の問い合わせで再利用されます。

```json
{
  "project_id": "my-gcp-project",
  "dataset_id": "analytics_123456789",
  "location": "プロパティにて設定された内容",
  "max_scan_gb_threshold": 3.0
}
```

## 7. 参考公式ドキュメントリンク集

- [GA4 BigQuery エクスポート スキーマ公式リファレンス](https://support.google.com/analytics/answer/7029846?hl=ja)
- [GA4 BigQuery サンプルクエリ集（Google公式）](https://developers.google.com/analytics/devguides/collection/ga4/bigquery_export?hl=ja)
- [BigQuery コスト最適化のベストプラクティス](https://cloud.google.com/bigquery/docs/best-practices-costs?hl=ja)
- [BigQuery × AI で 300 万円溶かそう](https://qiita.com/na0/items/e7eb24f896749fd3f190)
