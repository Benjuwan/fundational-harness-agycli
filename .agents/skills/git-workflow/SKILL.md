---
name: git-workflow
description: AIがブランチ作成・コミット・PR作成を行う際のGitワークフローとルール。ユーザーが「コミットして」「PRを作って」などGit操作を指示した際、または「/git-workflow」コマンドで呼び出された時に使用します。
---

# ブランチ・コミット・PR ガイドライン | Branch / Commit / PR Guidelines for AI
このガイドラインは、AIがブランチ作成・コミット・PR作成を自動実行する際に従うべき規約です。プロジェクトのルートに置いたAIのシステムプロンプト・憲法（例：GEMINI.md, AGENTS.md）から参照してください。

<instructions>

## 参照ファイル
| ファイル | 用途 |
|---|---|
| [`references/gh-cli-setup.md`](references/gh-cli-setup.md) | GitHub CLI（`gh`）の導入・認証・動作確認（macOS / Windows） |

## 1. ブランチ命名規則

### フォーマット
<type>/<issue番号>-<kebab-case-の説明>

### typeの一覧

| type | 用途 |
|------|------|
| `feature` | 新機能追加 |
| `fix` | バグ修正 |
| `refactor` | リファクタリング（振る舞い変更なし） |
| `docs` | ドキュメントのみの変更 |
| `test` | テストの追加・修正 |
| `chore` | ビルド・CI・依存関係などの変更 |
| `hotfix` | 本番緊急対応 |

### 命名例
feature/123-add-login-validation
fix/456-session-error-after-password-reset
refactor/789-extract-auth-service
docs/101-update-readme-setup
chore/update-eslint-config
hotfix/critical-payment-null-error

### ブランチ作成ルール
- **必ずデフォルトブランチ（`main`）の最新から切る**
- 1ブランチ = 1つの目的・1つのIssue
- ブランチ名は小文字・ハイフン区切り（スペース・アンダースコア禁止）
- Issue番号がある場合は必ず含める

### AIへの指示
#### ブランチ作成前に現在のブランチ状態やデフォルトブランチ（main, master, dev等）を確認する
```bash
git branch -a
git status
```

#### デフォルトブランチにチェックアウトして最新を取得する（mainの場合）
```bash
git checkout main && git pull origin main
```

#### ブランチを作成して移動
```bash
git checkout -b <type>/<issue番号>-<説明>
```

## 2. コミットメッセージ規約
- [Conventional Commits](https://www.conventionalcommits.org/) に準拠する

### フォーマット
<type>(<scope>): <subject>

[任意: body - なぜこの変更が必要か]

[任意: footer - Breaking Change / Issue参照]

### typeの一覧

| type | 用途 |
|------|------|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみ |
| `style` | フォーマット・空白など（ロジック変更なし） |
| `refactor` | リファクタリング |
| `test` | テストの追加・修正 |
| `chore` | ビルド・CI・依存関係 |
| `perf` | パフォーマンス改善 |
| `revert` | コミットの打ち消し（履歴は保持: 対象コミットを打ち消す新しいコミットを作成する） |

### コミットメッセージの書き方

**subject（1行目）のルール：**
- **原則として日本語で記述する**（`<type>(<scope>): <日本語の説明>`）。ユーザーから明示的な指示がない限り、英語のみの subject（例: `fix bug`, `update dependencies` 等）は禁止
- 50文字以内を目安
- 現在形・命令形で書く（`修正する` / `追加する` / `更新する`）
- 文末にピリオド不要
- 「何をしたか」より「**なぜしたか・何が変わるか**」を意識する

**body（任意）のルール：**
- 1行目と空行を1行挟む
- 「なぜこの変更が必要か」「何を考慮したか」を書く
- 72文字で折り返す

**良い例 / 悪い例：**

```bash
# 悪い例（何をしたか羅列するだけ、英語のみで概要が不明瞭）
git commit -m "ボタンの色を変更した"
git commit -m "fix bug"
git commit -m "update dependencies"
git commit -m "修正"

# 良い例（why + what が明確）
git commit -m "feat(auth): パスワードリセット後の自動ログイン機能を追加

セキュリティポリシー変更により、リセット後は再認証を必須とする。
セッション継続を廃止し、ログイン画面へリダイレクトする。
closes #456"

git commit -m "fix(ui): CTAボタンのコントラスト比をWCAG AA基準に修正

blue-400では基準値4.5:1を下回っていたためblue-600に変更。
closes #789"
```

### 1コミット = 1つの論理的変更
- 複数の関心事を1コミットに混在させない（1コミット1トピック）。レビューの目安として8ファイル・400行を超える場合はコミット分割を検討する。
- WIP（作業中）コミットはPR作成前に `git rebase -i` で squash する。ただし以下を遵守すること。
    - **自分しか触っていないブランチであることを必ず確認**:  
    ※共有ブランチ（main、develop など）に対して`rebase -i`を使うと、他のメンバーの履歴と衝突して大変なことになるため **自分しか触っていないブランチであることを必ず確認してから実施する**こと
    - **【AI実行環境の注意】**: AIのコマンド実行環境は非対話実行（TTY／エディタ無し）のため `git rebase -i` はハング／失敗する。AIが squash を行う場合は、以下の非対話代替を用いること。
        - `gh pr merge --squash`（GitHub 側で squash。本スキルは PR/`gh` 中心で相性が良い）
        - `git reset --soft <base> && git commit`（base 以降を1コミットへ集約。`--soft` は変更を破壊せず reflog で復元可）
- `git add -p` でハンクごとに追加し、意図しない変更を混入させない
    - **【AI実行環境の注意】**: `-p`（--patch）は非対話実行では使えないため、AIは `git add <file>` でパスを明示指定してステージすること（ハンク単位の対話選択は人間専用）。

> AIは以下内容を無視してください。このファイルを読む人間向けの備忘録的補足のメッセージです。
> - squash: 特定のコミット（上記例では`WIP`を指す）の内容を1つ、または意味のある単位にまとめること
> - ハンク: `git add -p`（--patch）を実行した際に表示される、変更内容のまとまり（同一ファイル内での各修正・編集箇所を指す）のこと

### Breaking Changeの書き方
```bash
git commit -m "feat(api)!: レスポンス形式をJSONに統一
BREAKING CHANGE: XMLレスポンスは廃止。
既存クライアントは移行ガイド(docs/migration.md)を参照。"
```

### プッシュはAIが実行しない（ユーザーの手動実行が必須）
`git push` はシステムファイル（`~/.gemini/antigravity-cli/settings.json`）内の制約（DENY）によって**物理的にブロック**される。  
AIはコミットまでを担当し、以下の手順でユーザーへ引き渡すこと。
1. コミット完了後、**現在のブランチ名を添えて**ユーザーへプッシュを依頼する。
2. ユーザーがプロンプト入力欄で以下を実行する（`!` プレフィックスにより、その場でコマンドが実行され結果がセッションに取り込まれる）。
   ```
   ! git push -u origin <ブランチ名>
   ```
3. プッシュ完了を確認してから、AIが `gh pr create` などのPR作成を行う。
   - `gh` が未導入・未認証の場合は [`references/gh-cli-setup.md`](references/gh-cli-setup.md) を案内する。

## 3. Pull Request規約

### PR タイトル
コミットメッセージと同じConventional Commits形式 + 日本語概要 + Issue番号
- **原則として日本語で記述する**（`<type>(<scope>): <日本語概要> #<Issue番号>`）。英語タイトルの使用は禁止。

フォーマット:
`<type>(<scope>): <日本語概要> #<Issue番号>`

命名例:
feat(auth): パスワードリセット後の自動ログイン機能を追加 #456
fix(ui): CTAボタンのコントラスト比をWCAG AA基準に修正 #789
chore(deps): 依存関係の更新と脆弱性の解消 #101

### PR 本文テンプレート

```markdown
## 概要
<!-- このPRで何をしたかを2〜3文で説明 -->

## 背景・目的
<!-- なぜこの変更が必要か。関連Issueへのリンク -->
closes #<issue番号>

## 変更内容
<!-- 主な変更点をリストアップ -->
-
-
-

## スコープ外（やっていないこと）
<!-- 今回あえて含めなかったことを明示 -->
-

## 動作確認方法
<!-- レビュアーがローカルで確認する手順 -->
1.
2.
3.

## スクリーンショット / 動画
<!-- UI変更がある場合は必須。Before / After形式で -->

| Before | After |
|--------|-------|
| <!-- 画像 --> | <!-- 画像 --> |

## チェックリスト
- [ ] セルフレビュー済み
- [ ] テストを追加・更新した
- [ ] 既存テストがすべて通る
- [ ] ドキュメントを更新した（必要な場合）
- [ ] Breaking Changeがある場合は明記した

## レビュアーへのメモ
<!-- 特に見てほしい箇所、迷った判断、懸念点などを事前に共有 -->

### PRの品質基準

**差分のサイズ：**
- 理想は **400行以内**。400行超の場合は分割を検討する
- 機械的な変更（リネーム・フォーマット）は別PRに切り出す

**Draft PRの活用：**
- 実装開始直後にDraft PRを立てて方向性を共有する
- レビュー依頼前に `Ready for review` に変更する

**セルフレビューの徹底：**
- アサイン前に自分でdiffを全行確認する
- コメントアウトされたコードが残っていないか確認する
```

## 4. マージ後のローカル後処理
マージ（ユーザーが GitHub の GUI で実施）の完了報告を受けたら、`gh pr view <PR番号> --json state,mergedAt` で確認し、承認を得てから実行する。

```bash
git switch <デフォルトブランチ>
git pull origin <デフォルトブランチ>
git branch -d <ブランチ名>
```

- `git branch -d` が「未マージ」として拒否した場合（squash / rebase マージ等）は、`-D` に切り替えずに停止して確認する。
- サンドボックスで `git pull` が失敗した場合は、回避策を試さず、ユーザーに `! git pull origin <デフォルトブランチ>` の実行を依頼する。
- サンドボックスで `.git/config` の更新に失敗した場合（`could not lock config file`）、ブランチ自体は削除されるが、`branch.<ブランチ名>.*` の設定が残る。ユーザーに `! git config --remove-section branch.<ブランチ名>` と `! git fetch --prune` の実行を依頼する。

</instructions>
