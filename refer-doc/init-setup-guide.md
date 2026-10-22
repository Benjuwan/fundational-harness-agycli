# Antigravity CLI 初期セットアップガイド
本ドキュメントは、ナレッジワーカー（非エンジニアを含む）が生成AIアシスタント環境「Antigravity」を安全かつスムーズに導入し、業務において自律的かつ高精度に運用するための必須初期セットアップ手順をまとめたガイドです。

## 1. はじめに
生成AIを単なる「一問一答のチャットツール」としてではなく、業務を安全かつ自律的に支援する「AIパートナー（ハーネス環境）」として活用するためには、セキュリティ設定・権限管理・外部ツール連携（MCP）・行動ルールやスキルの整備が不可欠です。

> [!TIP]
> **AIによる自動セットアップ（クイックスタート）**
> 本リポジトリのルートにある [**`README.md` の「クイックスタート（初回セットアップ）」**](../README.md#クイックスタート初回セットアップ) の案内に従い、以下の1行をチャット欄に送信すると、AIが下の「初回セットアップ手順（AI向けタスクフロー）」を読み取り、環境診断から初期設定までを自律的に進行します。
> ```text
> ./refer-doc/init-setup-guide.md の「初回セットアップ手順（AI向けタスクフロー）」を読んで初期設定を実行して
> ```

### 初回セットアップ手順（AI向けタスクフロー）
この指示を受け取ったAIは、以下のステップを順序通りに実行してください（※AIが当プロジェクトを初めて読み込む場合は、本ハーネスの概要説明を実施した後に以下のステップに進んでください）。

1. **ステップ1: 環境診断（Python / Node.js）**
   - `python --version`（または `python3`）および `node -v`, `npm -v` を実行してインストール状況を確認する。
   - **未導入のツールがある場合**:
     - 公式ダウンロードリンク（[Python](https://www.python.org/downloads/) / [Node.js](https://nodejs.org/)）を提示する。
       - **Windows 環境の場合**: PowerShell で npm / npx スクリプトの実行がブロックされるのを防ぐため、**管理者権限で起動した** PowerShell で `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` を実行する必要がある旨を案内する。（※管理者権限での起動方法も合わせて伝えること）
     - ユーザーに手動インストールおよびターミナル / CLI の再起動を促し、再起動後に再度上記プロンプトを実行するよう案内して作業を一時停止（待機）する。
   - **すべて導入済みの場合**: ステップ2へ進む。

2. **ステップ2: 設定ファイルの自律更新（サンドボックスバイパス）**
   - ユーザーに対し「不可視領域にある設定ファイル（`settings.json`）の手動編集ミスを防ぐため、AIが安全に追記・マージします。そのためにサンドボックスバイパスの承認が必要です」と理由を説明し、承認を求める。
   - ユーザーの承認後、Pythonのインライン処理（`python -c` または `python3 -c`）等をバイパス状態で実行し、既存設定を壊さず安全に辞書マージ（更新）する：
     - **ホスト設定（`settings.json`）**:
       - パス: Mac/Linux は `~/.gemini/antigravity-cli/settings.json`、Windows は `%USERPROFILE%\.gemini\antigravity-cli\settings.json`
       - 本ガイドの「[3. ステップ2: 必須初期設定 > (1) 行動制御・サンドボックス設定 (`settings.json`)](#1-行動制御サンドボックス設定-settingsjson)」に記載されている推奨設定（`permissions` 等、パスは現在のOS・プロジェクトの絶対パスに変換）を安全に追記・更新する。（※ステータスライン設定やキーバインド設定の詳細は「[6. 補足](#6-補足)」を参照するよう案内する）

3. **ステップ3: テレメトリのオプトアウト案内**
   - 個人アカウント等での不要な情報送信・学習利用を防ぐため、UI上で `/config` コマンドを実行し、「**Enable Telemetry（テレメトリを有効にする）**」をオフ（無効）にするようユーザーに案内する（詳細は「[4. ステップ3: セキュリティ・オプトアウト（学習拒否）・利用枠設定](#4-ステップ3-セキュリティオプトアウト学習拒否利用枠設定)」参照）。

4. **ステップ4: 反映確認とハーネス概要のガイダンス**
   - 設定の反映結果を報告し、本ハーネスの構成（`GEMINI.md`、ルール、サブエージェント、各種スキル）の全体概要と推奨される使い方を簡潔にガイダンスして完了を報告する（詳細は「[5. ステップ4: 基礎ハーネス同梱の推奨ルール・スキル・サブエージェント](#5-ステップ4-基礎ハーネス同梱の推奨ルールスキルサブエージェント)」参照）。

---

## 2. ステップ1: 必要なツールの準備
Antigravity 関連ツールには複数の種類が存在します。業務の自動化やコード・文書作成においては、ターミナル上で高度な自律処理を行う **Antigravity CLI** に加え、フックスクリプトや外部ツール連携（MCP）を動かすための **Python** および **Node.js** を準備します。

### ツールごとの特徴と使い分け

| ツール名 | 主な特徴と用途 | 推奨されるユースケース |
| :--- | :--- | :--- |
| **Antigravity CLI** | ターミナル上で動作する高機能エージェント環境。専門サブエージェントの独立並列起動、コンテキストの保護・分岐コマンド（`/btw`, `/fork`など）に対応。 | 複雑な多段階タスク、バックグラウンド処理、独立した分業・検証作業 |
| **Python** | フックスクリプト（`.agents/hooks/`）やデータ処理・業務自動化スクリプトの実行に必須。 | フックによる自律制御、データ集計・ファイル処理 |
| **Node.js (`npm` / `npx`)** | MCPサーバー（`playwright-mcp`, `context7` 等）の起動・連携に必須。 | ブラウザ自動操作、外部ツール連携 |

### インストール方法
- **Antigravity CLI**: 公式サイトの [Antigravity CLI ダウンロードページ](https://antigravity.google/download#antigravity-cli) からインストールします。
- **Python**: [Python 公式ダウンロードページ](https://www.python.org/downloads/) からインストールします。
- **Node.js**: [Node.js 公式ダウンロードページ](https://nodejs.org/) からインストールします（※Windows環境では、PowerShellでのスクリプト実行ブロックを防ぐため、管理者権限のPowerShellで `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` を実行してください）。

## 3. ステップ2: 必須初期設定

### (1) 行動制御・サンドボックス設定 (`settings.json`)
AIによる不必要なコマンド実行や取り返しのつかないファイル操作を防ぐため、ホスト環境の設定ファイルでサンドボックス機能とコマンド権限を定義します。

- **設定ファイルの配置場所**:
  `~/.gemini/antigravity-cli/settings.json`

```json
{
  "allowNonWorkspaceAccess": true,
  "enableTerminalSandbox": true,
  "notifications": true,
  "permissions": {
    "allow": [
      "mcp(context7/*)",
      "mcp(playwright/*)",
      "command(npm test.*)",
      "command(npm run .*)",
      "command(git diff)",
      "command(git status)",
      "command(git log)",
      "read_file(C:/Users/ユーザー名/Desktop/プロジェクト名/)",
      "write_file(C:/Users/ユーザー名/Desktop/プロジェクト名/)",
      "command(regex:python tasks/.*)",
      "command(regex:pytest tasks/.*)",
      "command(regex:node tasks/.*)"
    ],
    "deny": [
      "command(sudo)",
      "command(rm -rf)",
      "command(rm -fr)",
      "command(git push)",
      "command(git reset --hard)",
      "command(git clean)",
      "command(git checkout .)",
      "command(git restore .)",
      "read_file(C:/Users/ユーザー名/.ssh)",
      "read_file(C:/Users/ユーザー名/.aws)",
      "read_file(C:/Users/ユーザー名/.gnupg)",
      "read_file(C:/Users/ユーザー名/Desktop/プロジェクト名/.env)",
      "read_file(C:/Users/ユーザー名/Desktop/プロジェクト名/.dev.vars)",
      "write_file(C:/Users/ユーザー名/.ssh)",
      "write_file(C:/Users/ユーザー名/.aws)",
      "write_file(C:/Users/ユーザー名/.gnupg)",
      "write_file(C:/Users/ユーザー名/Desktop/プロジェクト名/.env)",
      "write_file(C:/Users/ユーザー名/Desktop/プロジェクト名/.dev.vars)"
    ],
    "ask": [
      "command(rm)",
      "command(rmdir)",
      "command(Remove-Item)",
      "command(del)",
      "command(rd)",
      "command(git worktree)",
      "command(git rebase)",
      "command(git checkout --)",
      "command(git stash drop)",
      "command(git stash clear)",
      "command(git branch -D)",
      "command(git branch -d)"
    ]
  },
  "runningLightSpeed": "fast",
  "toolPermission": "proceed-in-sandbox"
}
```
※上記の `C:/Users/ユーザー名/Desktop/プロジェクト名/` などのパス指定は、ご利用のOS（Mac/Linux または Windows）および実際のプロジェクトディレクトリの絶対パスに置き換えて設定してください。

> [!IMPORTANT]
> **権限設定 (`permissions`) の考え方**
> - **`allow`**: ユーザーの都度確認なしでAIが自律実行できる安全なコマンドを指定します。
> - **`deny`**: ユーザーが指示や承認を出した場合でも、**AIに実行を固く禁止（ガード）するコマンド**を指定します。
> - ※`git`などエンジニア向け関連の記述が一部含まれているのは将来の拡張性を加味してです。

> [!TIP]
> **モデル選定指針 (Pro vs Flash の使い分け)**
> 業務タスクの性質に応じて、適切なモデルを選択・設定することが推奨されます。
> 
> - **Flash モデル (`Gemini 3.0 Flash` 等)**:
>   - **適したタスク**: 単調かつ処理工数の少ないタスク（単一ファイルの軽微な誤字修正、単純な文章の要約・翻訳、簡単なスクリプト実行等）。
>   - **特徴**: レスポンスが高速で低コスト。
> - **Pro モデル (`Gemini 3.1 Pro (High)` 等)**:
>   - **適したタスク**: 「長文脈 × 複雑な推論 × 多段階処理」（複雑なコード・ドキュメント実装、多段階修正、深層調査、多角的な品質検証・監査等）。
>   - **必須となる理由**: 高度かつ多段階なタスクにおいて Flash モデルを使用すると、文脈の忘却、複雑な条件の無視、明確な精度劣化や思考破綻（ハルシネーションや不整合な出力）が発生します。そのため、本ハーネスにおける本格的な業務支援・開発・検証作業では **Pro モデルの採用が不可欠**です。

### (2) MCP (Model Context Protocol) 設定 (`.agents/mcp_config.json`)
MCPは、AIエージェントが外部ツールやブラウザ、データベースなどと連携するための標準規格です。

- **設定ファイルの配置場所**:
  プロジェクトルート内の `.agents/mcp_config.json`

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@playwright/mcp@latest"
      ]
    },
    "context7": {
      "command": "npx",
      "args": [
        "-y",
        "@upstash/context7-mcp"
      ]
    }
  }
}
```

#### 本プロジェクトで導入されている標準MCP
- **`playwright-mcp`**: ブラウザの自動操作、アクセシビリティツリーの読み取り、画面探索、E2Eテスト検証を行うための標準MCPツール。
- **`context7`**: 利用しているライブラリやフレームワークの最新ドキュメント情報を正確に取得・検索するためのツール。

> [!NOTE]
> 本基礎ハーネスでは、**非エンジニア（ナレッジワーカー）に対する `npm` や `package.json` の管理負担・パッケージ競合トラブルを回避するため、`playwright-mcp` (`.agents/mcp_config.json`) を設定・利用する方針**を採用しています。これにより、環境構築の複雑化を防ぎ、導入直後から安全にブラウザ操作・UI確認を実行できます。

---

> [!IMPORTANT]
> **`mcp_config.json` 記述時の注意点**
> Antigravity CLI は `mcp_config.json` 内のコードコメント（`// ...`）をパースできません。コメントを記述すると読み込みエラーの原因となるため、**コメントは一切含めない JSON 形式**で作成してください。また、`args` に `"-y"` を指定してインタラクティブな確認プロンプトによる処理停止を防ぎます。

### (3) 最上位ルール（`GEMINI.md`）とハーネスディレクトリ構成 (`.agents/`)
AIが起動時に真っ先に読み込む最上位の規範（システムプロンプト）とハーネス構造を配置します。

#### 最上位ルール (`GEMINI.md`)
プロジェクトルートに配置します。AIに対する行動方針・禁止事項・事前承認（HITL）のルールを記述します。
※応答品質と遵守率を維持するため、**`GEMINI.md` は 200 行以内に収める**ことが推奨されます。

#### ハーネスディレクトリ構成 (`.agents/`)

```
プロジェクトルート/
├── GEMINI.md         ← 最上位の憲法・行動規範（システムプロンプト）
└── .agents/
    ├── agents/       ← サブエージェント定義（専門役割のAI）
    ├── rules/        ← ルールファイル群（作業手順・安全制約・品質規定）
    ├── skills/       ← スキル群（定型業務のナレッジと実行手順）
    ├── hooks/        ← フック用スクリプト群（自動検証・制御コード）
    ├── hooks.json    ← フック設定ファイル（ワークスペース単位。同梱済み）
    └── mcp_config.json ← MCP設定ファイル
```

## 4. ステップ3: セキュリティ・オプトアウト（学習拒否）・利用枠設定
生成AIを業務利用する際、入力データのセキュリティ保護とAPIキーの課金管理は極めて重要です。

### (1) Googleアカウント/API利用時の注意点
- **個人向け有料アカウントの注意点**:
  Web版「Google One AI Premium (Google AI Pro)」等を契約していても、**API（Google AI Studio）からの呼び出しは、従量課金（Pay-as-you-go）登録をしていない限り「無料枠（レートリミット等の制限あり）」扱い**となります。
- **法人向けアカウント（Workspace）との違い**:
  法人向け Google Workspace アカウントは規約上データが学習利用されませんが、**個人向けアカウントは有料であっても初期設定でモデル学習の対象**となります。

### (2) 学習拒否（オプトアウト）とテレメトリ設定
個人向けアカウント利用時や情報漏洩を予防するため、オプトアウト設定を行います。

1. CLI上で **`/config`** コマンドを実行し、設定画面を開きます。
2. **`Enable Telemetry`（テレメトリの有効化）を オフ（Disabled）** に変更します。

> [!WARNING]
> **オプトアウトに関する留意事項**
> テレメトリをオフにすることで利用状況データの送信を拒否（オプトアウト）できますが、Googleの規約上「100%学習に使用されない」ことが完全に保証・明言されているわけではありません。社外秘・機密情報の扱いには十分注意してください。

### (3) APIキーの管理・アクセス制限・予算アラート
APIキーの漏洩による予期せぬ課金トラブルを防止するため、以下のセキュリティ対策を実施してください。

1. **APIキーを直接コードに書かない**:
   HTMLやJavaScript等のフロントエンドコードにAPIキーを直書きせず、環境変数やバックエンド経由で参照します。
2. **APIキーの利用サービス制限**:
   [GCPコンソール](https://console.cloud.google.com/) の「認証情報 - APIとサービス」から、対象のAPIキーの利用範囲を **`Gemini API` (Generative Language API) のみに制限**します。
3. **1日あたりの割当上限（Quotas）の設定**:
   万が一キーが露出した場合の被害を抑えるため、GCPの「割り当て（Quotas）」設定で1日あたりのリクエスト数上限を最小限に設定します。
4. **予算とアラートの設定**:
   有料の従量課金（Pay-as-you-go）を利用する場合は、GCPの「予算とアラート」機能を有効にし、指定金額に達した際に即座に通知が届くよう設定します。

## 5. ステップ4: 基礎ハーネス同梱の推奨ルール・スキル・サブエージェント
本ハーネス環境には、ナレッジワーカーが安全かつ効率的に作業を進められるよう、あらかじめ各種ルール・スキル・サブエージェントが組み込まれています。

### (1) ルール一覧 (`.agents/rules/`)

| ルール名 | 概要と主な目的 |
| :--- | :--- |
| **`cognitive-refresh.md`** | 長時間セッションや文脈圧迫時の指示忘却を防ぐ「認知的リフレッシュ」の手順。 |
| **`communication-policy.md`** | 日本語対応、不確実性の明確化、推測での単独作業禁止など対話マナー規定。 |
| **`hitl-policy.md`** | ファイルの大幅な変更や外部送信・生成前の「y/n」事前承認原則（絶対優先）。 |
| **`minimal-security-guidelines.md`** | `.env` や認証情報など機密データの漏洩・ログ混入防止セキュリティルール。 |
| **`output-quality-guidelines.md`** | ビジネス文書作成・要約・レビューにおけるアウトプット品質規定と承認プロセス。 |
| **`over-engineering-prevention.md`** | 指示されていない周辺コード・ファイルの勝手な改修（過剰推論）を防止。 |
| **`subagent-policy.md`** | サブエージェント利用時のユーザー承認、ミッション・ブリーフ、失敗時対応などの厳格な運用ルール。 |
| **`troubleshooting.md`** | エラー発生時に場当たり的対応を避け、根本原因（RCA）を特定するルール。 |
| **`workflow.md`** | タスク実行前の計画策定（プランモード）、チェックリスト更新、サブエージェント運用規定。 |

### (2) スキル一覧 (`.agents/skills/`)

| スキル名 | 概要と主な用途 |
| :--- | :--- |
| **`bq-analysis`** | 自然言語から BigQuery 用 SQL を自動生成し、GA4 データの抽出・集計・分析を安全かつコスト意識下で実行。 |
| **`digital-shift`** | 手書きの紙資料や PDF/画像を、原本に忠実な文字起こしと構造化 Markdown に変換するデジタル化スキル。 |
| **`document-reviewer`** | 社内文書や企画書などのドラフトに対し、建設的・客観的なレビューを実施。 |
| **`document-risk-review`** | 業務ドキュメントやマニュアル、自動化要件の抜け漏れ・考慮不足・リスクを検出。 |
| **`domain-modeling`** | ドメイン用語や `CONTEXT.md`、ADR の整理・定義を支援し、プロジェクトの理解を整理。 |
| **`explain-visually`** | 長大なドキュメントや設計を読み解き、Mermaid や HTML で視覚的に説明するスキル。 |
| **`fundamental-rca`** | 不具合・ミス発生時に、論理的な根本原因分析（RCA）と再発防止策を立案。 |
| **`git-workflow`** | ブランチ作成・コミット・PR作成などのGit操作を安全かつ標準化された手順で実行。 |
| **`grill-with-docs`** | ドキュメントや設計書を根拠に、要件の曖昧さを掘り下げて確認する対話型レビュー支援。 |
| **`grilling`** | 指示が曖昧な場合に、AIから鋭い逆質問を行い要件・方針の解像度を高める壁打ちスキル。 |
| **`handover`** | 会話の区切りや作業中断時に、次回チャットに引き継ぐ `HANDOVER.md` を自動整理。 |
| **`multi-persona-site-audit`** | 実サイトを複数のペルソナ視点で監査し、改善仮説と優先度付けを支援。 |
| **`presentation-slider-creator`** | テキストやドキュメントから Marp 形式のプレゼンスライドを自動生成。 |

### (3) サブエージェント一覧 (`.agents/agents/`)

| サブエージェント名 | 専門役割と担当業務 |
| :--- | :--- |
| **`handwritten-doc-extractor`** | 手書き資料・契約書・画像/PDF を正確に読み取り、原本に忠実な文字起こしと Markdown 構造化を行うマルチモーダル専門員。 |
| **`image-processor`** | 画像のリサイズ・リネーム・最適化など画像処理用スクリプトの自律構築と実行。 |
| **`implementer-agent`** | メインAIの指示に基づき、フェーズ分け・実装・セルフレビューを正確に行う実装専門員。 |
| **`qa-auditor`** | UI・コード・ドキュメントの多角的レビューと事実確認を行う独立QA監査員。 |
| **`task-executor`** | メインAIの指示に基づき、タスクの細分化・自律実行・セルフレビューを行う実行専門員。 |

> [!NOTE]
> **サブエージェント起動の仕様（公式仕様準拠・直接起動一本化）**
> 各サブエージェント定義ファイル（`.agents/agents/*.md`）のフロントマターにおいて、公式仕様に準拠して `tools: [view_file, replace_file_content, ...]` と利用ツールを明示列挙することで、`invoke_subagent` の `TypeName`（例: `TypeName: "implementer-agent"`）で **直接起動** して必要なツールが正常に付与されます。旧来のオーバーソウルアプローチ（`self` へのプロンプト憑依）は廃止されました。詳細な経緯については [**サブエージェント認識およびツール制限の仕様と本プロジェクトの対応**](./subagent_discovery_issue.md) を参照してください。

## 6. 補足

### 6-a: フック（Hooks）の設定 / フック（Hooks）の概要
フックとは、Antigravity CLI の実行ループ（モデルへのプロンプト送信前 `PreInvocation` など）の特定のタイミングで、自動的にカスタムスクリプトを呼び出す拡張機能です。コンテキスト圧縮時に最優先ルールを自動で動的再注入したり、会話ログからセッション切り替えを促す警告を出力するなど、高度な自律制御や品質担保を実現できます。

#### 詳しい設定方法
フックの登録手順、OSごとのコマンド指定（Mac: `python3` / Windows: `python`）、同梱スクリプトの詳細については、以下のガイドを参照してください。  
👉 [**フック（Hooks）初期設定・運用ガイド**](./hook-setup-guide.md)

#### ステータスラインの設定について
[Antigravity CLI でコンテキスト使用率などの情報をステータスラインに表示する方法](https://zenn.dev/benjuwan/articles/96639c465ac232)で詳細な設定を記述しています。  
記事内の情報ソースは[antigravity-cli リポジトリ](https://github.com/google-antigravity/antigravity-cli/tree/main)内の[`statusline.sh`](https://github.com/google-antigravity/antigravity-cli/blob/main/examples/statusline/statusline.sh)ページです。

### 任意： キーバインド設定（ショートカットキー変更）について
Antigravity CLI 利用時のキーバインド設定ファイルです。

- **設定ファイル**: `~/.gemini/antigravity-cli/keybindings.json`:  サブエージェント利用時の承認ダイアログコマンド（ショートカットキー）
```json
{
  "subagent.approve_fast": ["ctrl+k"],
  "subagent.jump_to_waiting": ["alt+j"]
}
```

> [!WARNING]
> **記述・保存時の注意点**:
> - **カンマ（`,`）の扱い**: 要素間の区切りには必須ですが、**末尾カンマ（Trailing Comma）は構文エラーになるため禁止**です。
> - **文字コード**: UTF-8 BOM が混入するとパースエラーになるため、必ず **BOM なし UTF-8** で保存してください。
> - **設定反映**: 起動時のみ読み込まれるため CLI の再起動が必要です（リセットはファイル削除後に `/keybindings` を実行）。

> [!IMPORTANT]
> **VSCode 統合ターミナル利用時の必須設定（キー横取り回避）**:
> - **必要な理由**: VSCode ではデフォルトで **`Ctrl+K` がショートカット（Chord 待機キー）として横取り**され、CLI の即時承認にキーストロークが届きません。
> - **対処法**: VSCode の `settings.json`（ワークスペースの `.vscode/settings.json` または `Ctrl+Shift+P` → `Preferences: Open User Settings (JSON)`）に以下を追記し、ウィンドウを再読み込みしてください。
>   ```json
>   {
>     "terminal.integrated.allowChords": false
>   }
>   ```
