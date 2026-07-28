# Antigravity CLI（および Antigravity IDE）用の汎用ハーネス
このリポジトリ（`fundational-harness-agycli`）は、一般ビジネスユーザー（ナレッジワーカー）が日常業務でAIエージェント（[Antigravity CLI](https://antigravity.google/product/antigravity-cli)または
[Antigravity IDE](https://antigravity.google/product/antigravity-ide)）を安全かつ効率的に活用するための「汎用的なルール・スキル・サブエージェント」のファイルセット（ハーネス）です。  
`fundational-harness`という名前の通り、**化粧のファンデーションと同じように「当リポジトリを下地にして各組織（企業）や各人用にカスタマイズ」してもらう想定**です。

> [!NOTE]
> ※単体エージェントのみの Antigravity IDE ではサブエージェントによる並列作業/コンテキストの負荷軽減が行えないので基本的には Antigravity CLI を推奨します。

---

- [Antigravity CLI 公式ドキュメント](https://antigravity.google/docs/cli/overview)
- [Antigravity IDE 公式ドキュメント](https://antigravity.google/docs/ide/overview)

## AIの学習について（情報漏洩のリスクヘッジ）
Gemini（Google）では、個人有料アカウント（Google AI Pro など）であってもサブスク利用だとAI学習に利用されます。センシティブまたはクレデンシャルな情報を含むビジネスユースを想定する場合は Google Workspace または API の従量課金利用が推奨されます。Google Workspace または API の従量課金利用の場合はデフォルトで学習されないようになっています。

## ハーネス（AI利活用環境ファイル）について
本リポジトリでは「ハーネス（AI利活用環境ファイル）」を、以下のファイルセットから構成される仕組み（AI利用時の安全なガードレール）と定義しています。

### システムプロンプト・憲法（`GEMINI.md`）: 
AIの行動規範となる最優先ルールファイル

### サブエージェント（`.agents/agents`）: 
タスクを並列処理する専門アシスタント。作業を分担することでメインエージェントの記憶容量（コンテキスト）の圧迫を防ぎ、回答精度を保ちます。

### ルール（`.agents/rules`）: 
タスク実行時や特定フェーズ（対話、レビュー、安全確認など）における具体的な運用ルール

### スキル（`.agents/skills`）: 
定型業務や特定作業をAIに実行（作業代行）してもらうための標準手順書（マニュアル）ファイル

### フック（`.agents/hooks`）: 
特定フェーズ時に発動するシステム制約。これにより自動的に発動する機能を付与したり、AI制御を実現できたりする。  
※フックの設定に関しては[`hook-setup-guide.md`](./refer-doc/hook-setup-guide.md)に詳細を記載しています。本リポジトリのフック（`.agents/hooks`）を設定する場合（初期設定時）は、AIに「`./refer-doc/hook-setup-guide.md`を参照して`.agents/hooks`内にある各種フックの設定を行って」とプロンプト入力すれば済むと思います。

> [!NOTE]
> 各種フックはPythonスクリプトなので[Download Python | Python.org](https://www.python.org/downloads/)からPythonをインストールしてください。

### MCP（`.agents/mcp_config.json`）: 
AIと外部サービスをつないで、AIの対応範囲を拡張するための規格（仕組み）。

## プロジェクト構成とプラグイン構成の違い
Antigravity CLI では、カスタムルール・スキル・サブエージェントを読み込む仕組みとして、**「プロジェクトローカル構成（.agents/）」** と **「公式プラグイン構成（plugins/）」** の2種類のディレクトリ構造をサポートしています。  
Antigravity CLI の内部ロジックにおいて両方の自動検出・ロードに対応しているため、**どちらの構造で配置しても機能上の違いはなく、ルールやスキルは同等に正常動作**します。利用用途や運用スタイルに合わせて選択してください。

### 1. プロジェクトローカル構成（本リポジトリの標準構造）
プロジェクトのルートディレクトリに `.agents/` フォルダを配置する構造です（`.agents/rules/`, `.agents/skills/`, `.agents/agents/` など）。

- **適用場所**: プロジェクト内（リポジトリ内）のみ
- **メリット**:
  - Git などでコードと一緒に管理できるため、**チームメンバー全員でまったく同じルールやスキルを共有・強制しやすい**。
  - プロジェクト固有の制約（社内用語、指定のコード規約など）に合わせた細かなカスタマイズが容易。
- **デメリット**:
  - 他のプロジェクトや別ディレクトリで作業する際には設定が引き継がれない。

### 2. 公式プラグイン構成（公式ドキュメント `features` 記載の構造）
公式ドキュメント（[Features: Plugins](https://antigravity.google/docs/cli/features#plugins)）で解説されている構造です。`~/.gemini/antigravity-cli/plugins/<plugin_name>/` 配下（OSホスト環境）にマーカーファイル（`plugin.json`）とともに配置します。

- **適用場所**: PC（マシン）全域のすべての作業ディレクトリ
- **メリット**:
  - どのプロジェクトやディレクトリで CLI を起動しても、**常に同じルール・スキル・品質で AI を活用できる**。
  - 共通の汎用ハーネス（リサーチ、資料作成、文書レビューなど）として組織内へ一括配布しやすい。
- **デメリット**:
  - プロジェクトごとの特殊な個別ルールや限定的な制約に対応させづらい。
