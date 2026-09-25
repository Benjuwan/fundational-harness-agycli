# Antigravity CLIにおけるサブエージェント認識およびツール制限の仕様と本プロジェクトの対応

> [!IMPORTANT]
> ## ステータス: 解決済み（2026-09-23 調査完了）
> 「カスタムサブエージェントを `invoke_subagent` で直接起動するとツール（手足）が付与されない」問題は **是正されていた**。  
> 根本原因は **Antigravity CLI のバグではなく、本プロジェクトのフロントマター記述が公式仕様と不一致だったこと** にある（後述「[3. 根本原因](#3-根本原因フロントマターキーの不一致)」参照）。  
> 今後は「**直接起動一本化（オーバーソウルアプローチ廃止・アーカイブ化）**」で運用する（後述「[5. 今後の運用方針](#5-今後の運用方針直接起動一本化)」参照）。

---

## 1. 概要

本ドキュメントは、本プロジェクトにおいてカスタムサブエージェントを `invoke_subagent` ツールで直接起動（`TypeName` にカスタム名を指定）した際に「ファイル操作等の必須ツールが一切付与されず、実作業が不可能な状態に陥る」という事象が発生した背景、原因調査の経緯、根本原因の特定、および今後の運用方針をまとめたものです。

---

## 2. 問題の経緯

### 2-1. 過去の事象（旧バージョン）
- `invoke_subagent` でカスタム名を指定すると `not found or not allowed to be invoked` で**起動自体が物理的に拒否**されていた。

### 2-2. 中間の事象（アップデート後）
- システムのアップデートにより **起動（ディスカバリ）自体は成功** するようになった。
- しかし、起動したサブエージェントに `view_file` や `run_command` 等の必須ツールが付与されず、`send_message` と `schedule` のみが利用可能な「手足のない状態」になっていた。
- `enable_write_tools: true` を明記しても状況は変わらなかった。

### 2-3. 暫定対応（オーバーソウル・ワークアラウンド）
上記の事象を受け、本プロジェクトでは以下のアドホックな運用を採用していた：

1. すべてのツール権限が保証されている組み込みサブエージェント（`TypeName: "self"`）を代用
2. `utils/generate_subagent_prompt.py` により、カスタムエージェントの役割・制約・コンテキストを `self` の Prompt にインジェクション
3. 「完全なツール（手足）を持った `self` に、カスタムエージェントの役割（頭脳）をインストールする」形で期待する振る舞いを再現

---

## 3. 根本原因：フロントマターキーの不一致

### 3-1. 調査方法と公式ドキュメント参照リンク
- **公式ドキュメント（Web）**:
  - [Google Antigravity Docs - Custom Subagents](https://antigravity.google/docs/subagents)
  - [Custom Subagents - Invoking Subagents](https://antigravity.google/docs/subagents/#invoking-subagents)
  - [Custom Subagents - Markdown Format & Frontmatter](https://antigravity.google/docs/subagents/#custom-agents-markdown-format)
  - [CLI Agent Manager Panel (/agents)](https://antigravity.google/docs/cli/commands/agents)
- **調査ツール**:
  - **Playwright MCP**: 公式ドキュメント SPA（https://antigravity.google/docs/subagents/#invoking-subagents ）のブラウザ直接レンダリングとスナップショット検証
  - **Context7 MCP**: `/websites/antigravity_google`（クエリ: `subagents configuration frontmatter invoking subagents tools`）による最新APIドキュメントおよびコード例の抽出照合
  - **現行ランタイム環境**: システムプロンプト内 `<subagents>` セクションおよびツールスキーマの確認

### 3-2. 発見された事実

Antigravity CLI には **2つの異なるサブエージェント設定体系** が存在する：

| 設定方式 | 用途 | ツール権限の指定方法 |
| :-- | :-- | :-- |
| **静的定義（`.md` フロントマター）** | `.agents/agents/<name>.md` に記述する永続的な定義 | **`tools: [view_file, run_command, ...]`**<br>（個別ツール名の `string[]` 型で明示列挙） |
| **動的定義（`define_subagent` ツール）** | セッション中に一時的に作成する定義 | **`enable_write_tools: true`**<br>（`boolean` 型のカテゴリフラグ） |

**本プロジェクトの `.md` ファイルは、動的定義（`define_subagent`）用のキー名を静的定義（`.md`）のフロントマターに記述していた。**

```yaml
# ❌ 当プロジェクトの既存記述（誤り）
---
name: implementer-agent
kind: local                    # ← 公式仕様に存在しないキー
enable_write_tools: true       # ← define_subagent 専用。.md では無視される
enable_mcp_tools: true         # ← 同上
temperature: 0.1               # ← 公式仕様に存在しないキー
max_turns: 30                  # ← 公式仕様に存在しないキー
---
```

```yaml
# ✅ 公式仕様に準拠した正しい記述
---
name: implementer-agent
description: メインエージェントの指示に基づき実装を行う専門エージェント
tools:
  - view_file
  - replace_file_content
  - write_to_file
  - run_command
subagent: true
model: inherit
commandExecutionPolicy: sandbox
---
```

パーサーは認識しないキー（`enable_write_tools` 等）を無視し、`tools` のデフォルト値 `[]`（空配列）を適用する。結果として「ツールが一切付与されない」状態が発生していた。

### 3-3. つまり何が起きていたのか

「CLIのバグ」ではなく、**本プロジェクト側の設定ミス**だった。公式仕様に準拠した `tools` キーでツールを明示的に列挙すれば、カスタムサブエージェントの直接起動でツールが正しく付与される。

### 3-4. 公式仕様のフロントマター全キー一覧

公式ドキュメント（https://antigravity.google/docs/subagents ）より：

| Property | Type | Default | Description |
| :-- | :-- | :-- | :-- |
| `name` | `string` | *(Required)* | 一意識別子 |
| `description` | `string` | *(Required)* | プランナーの委譲判断用の説明 |
| `tools` | `string[]` | `[]` | 許可ツールの明示リスト |
| `subagent` | `boolean` | `true` | `invoke_subagent` 経由の起動許可 |
| `mainAgent` | `boolean` | `true` | チャット UI でのプライマリ選択許可 |
| `model` | `string` | `inherit` | モデルティア（`inherit`, `flash`, `pro`） |
| `commandExecutionPolicy` | `string` | `sandbox` | シェル実行ポリシー（`off`, `auto`, `eager`, `sandbox`） |
| `mcpServers` | `object[]` | `[]` | MCP サーバー設定 |
| `skills` / `plugins` | `string[]` | `[]` | 依存スキル・プラグイン |

> [!WARNING]
> **Known Issue（公式記載）**: `tools` リストに存在しないツール名やスペルミスを含めると、サブエージェントのプロセスがハングする不具合が報告されている。ツール名は正確に指定すること。

---

## 4. オーバーソウル廃止と直接起動一本化に至った経緯

### 4-1. 過去にオーバーソウルが果たしていた役割
- ツール欠落の回避（`self` は親のツールを完全継承するため、動的定義キー誤記によるツール剥奪を回避できた）
- カスタムエージェントの役割・制約のインジェクション

### 4-2. ハイブリッド方式の検討と却下理由
調査初期には「直接起動を標準としつつ、オーバーソウルを特殊用途（文脈継承など）として残すハイブリッド方式」も検討されたが、ユーザーとの議論により**却下**された。理由は以下の通りである：

1. **AIの判断コストとルールの形骸化（LITM）**:  
   2つの方式を併用する使い分けルールは、LLMにとって認知的負荷が高く、コンテキスト圧迫時に判断基準を忘却（Lost in the Middle）するリスクがある。
2. **安全側バイアスによる形骸化**:  
   「全ツールが使える」という安心感から、AIが安易にオーバーソウルへ逃げ続け、本来の直接起動アプローチが形骸化する恐れがある。
3. **オーバーソウル固有メリットの代替可能性**:  
   親の動的コンテキスト（作業履歴や中間成果物）は、`invoke_subagent` 呼び出し時の `Prompt` 引数に申し送り事項を明記することで十分に伝達可能である。

したがって、オーバーソウルアプローチは完全に**廃止（アーカイブ化）**し、直接起動へ一本化することを決定した。

---

## 5. 今後の運用方針（直接起動一本化）

### 5-1. 直接起動への完全一本化
すべてのカスタムサブエージェントは、`invoke_subagent` ツールを用いて直接起動する。

- `.agents/agents/<name>.md` のフロントマターを公式仕様に準拠させ、`tools` キーで必要なツールを明示列挙する。
- `invoke_subagent(TypeName: "<カスタム名>")` で直接起動する。
- メリット: クリーンなアーキテクチャ、適切なツール制限（最小権限の原則）、プロンプト生成スクリプトや一時ファイル（`tasks/tmp/*_input.txt` 等）の排除。

### 5-2. 動的コンテキスト伝達の運用（Prompt経由）
直接起動のサブエージェントはクリーンスレート（Context Isolation）で起動されるため、親エージェントが持つ最新の作業進捗や申し送り事項は、`invoke_subagent` の `Prompt` 引数に必要な要点を構造化して直接渡す運用とする。

### 5-3. `generate_subagent_prompt.py` のアーカイブ化
- `generate_subagent_prompt.py` は通常運用から退役させ、`refer-doc/archived/` ディレクトリ配下に移動（アーカイブ化）した。
- 将来的な参照・万一の復帰用（通常手順で行き詰まりが発生した際のフォールバック）としてコード自体は残すが、通常のワークフローからは完全に除外する。

### 5-4. ルールファイルおよびスキルの整合性確保
- `workflow.md`, `subagent-policy.md` に記載されている「オーバーソウル（憑依）アプローチ」「第1アプローチ」等の手順を撤廃し、直接起動を前提とした簡潔・堅牢な手順へ改訂する。
- `multi-persona-site-audit/SKILL.md` など、オーバーソウル前提の記述を含むスキルファイルを修正する。

---

---

## 6. 移行時の注意事項

### 6-1. フロントマター修正時の注意
- **`tools` に指定するツール名は正確に記述すること**（Known Issue: スペルミスでハングする）
- 公式例に確認できるツール名: `view_file`, `replace_file_content`, `write_to_file`, `run_command`, `grep_search`
- MCP ツール（Playwright 等）は `tools` ではなく `mcpServers` キーで設定が必要な可能性がある（要検証）
- `skills` キーでスキルの依存を明示指定する必要がある（例: `skills: [skills/modern-web-guidance]`）

### 6-2. 段階的な移行を推奨
一括修正ではなく、1つのエージェント（例: `security-auditor`）で実機検証してから全面展開すること。

---

## 付録: 過去の調査履歴（アーカイブ）

<details>
<summary>過去のCLI仕様と既知の挙動（問題の背景）</summary>

トラブルシューティングの過程で、かつては以下の仕様・問題が確認されていました。

> *"Some versions of the CLI have historically exhibited behavior where they prioritize scanning agents bundled within plugins/ directories over loose files in a top-level .agents/agents/ folder. If you find your custom agents are not being discovered, try moving the agent definition (the agent.json or markdown file) into the agents/ folder of an active plugin directory to ensure the CLI scanner picks it up correctly."*

- ※この情報は Web 検索で取得したもの。Antigravity公式サイト（`antigravity.google`）のドキュメントSPA内の記述を検索エンジンが要約した結果。

**【意訳・解釈】**
過去のCLIの一部バージョンでは、トップレベルの `.agents/agents/` にあるファイルよりも、`plugins/` ディレクトリ配下にバンドルされたエージェントのスキャンを優先する傾向がありました。もし認識されない場合は、プラグインディレクトリ内の `agents/` フォルダへ移動する回避策が推奨されていました。

</details>

<details>
<summary>プロジェクト内での過去の検証と判明した実情</summary>

1. **過去のプラグイン配置や動的登録の限界**:
   過去、`plugins` 配下に置くことでAIのコンテキストには読み込まれましたが、`invoke_subagent` ツールが許容するリストには自動追加されませんでした。また、`define_subagent` ツールで動的に定義しても起動が拒否される（`not allowed`）という基盤のホワイトリスト制御の壁がありました。

2. **アイデンティティ（役割）の付与は成功する**:
   システムアップデートにより、`.agents/agents/` 配下に配置した定義ファイル（`.md`）の内容はシステムに正しく認識されており、直接起動時にサブエージェントのシステムプロンプトへ自動でインジェクションされるようになっています。

3. **ツールの欠落（当時の事象）**:
   役割を理解していても、システムから必須ツールが付与されなかった。
   > *"現在、私の環境には `view_file` や `run_command` といったファイルシステムにアクセスするためのツールが付与されていません（確認できる利用可能なツールは `send_message` と `schedule` 等に限られています）。"*

4. **【原因（当時の考察→誤り）】**:
   当時は「システムの根幹的な仕様・バグ」と判断していたが、実際には**フロントマターのキー名不一致**（`enable_write_tools` ≠ `tools`）が原因だった。`enable_write_tools` は `define_subagent`（動的定義）専用のパラメータであり、静的 `.md` のフロントマターでは認識されないため、`tools` のデフォルト値 `[]` が適用されていた。

</details>

<details>
<summary>ワークスペースローカルなプラグイン構成による解決の検討（不採用）</summary>

ワークスペース内に `plugins/` フォルダを作成する回避策を検討したが、以下の理由で不採用とした：

1. **プラグインはグローバル配置が前提**: `~/.gemini/antigravity-cli/plugins/` へのステージングが前提
2. **ワークスペースの拡張は `.agents` が公式ルート**: `.agents/agents/` への配置がアーキテクチャとして正しい
3. **ホスト環境汚染の懸念**: 二重管理、ポータビリティ低下、セキュリティリスク

※根本原因がフロントマターのキー名不一致であったため、プラグイン構成への移行はそもそも不要だった。

</details>

<details>
<summary>旧バージョンでの動作確認ログ</summary>

```bash
### 4. 利用可能な専用エージェント (Subagents)
  
  本プロジェクト独自の運用エージェントとして以下を認識しています。
  
  •  es5931-article-data-extractor 
  •  image-processor 
  •  implementer-agent 
  •  qa-auditor 
  •  security-auditor 
  •  static-site-planner 
  
  ※他にシステムのデフォルト提供エージェントとして  research  および  self  を認識しています。      

────────────────────────────────────────────────────────────
> カスタムサブエージェント認識できるようになったのですか？

▸ Thought for 2s, 621 tokens
  Prioritizing Tool Usage
  はい。現在の環境では、システム起動時に提供されるコンテキスト情報（ <subagents> 
  セクション）内に、本プロジェクト専用のカスタムサブエージェントがあらかじめ一覧として読み込まれて 
  おり、認識できるようになっています。
  
  これにより、既存の組み込みエージェント（ research  や  self ）と同様に、 invoke_subagent         
  ツールを用いて  implementer-agent  や  qa-auditor 
  などの専用エージェントを直接指定して呼び出すことが可能になっています。
```

</details>
