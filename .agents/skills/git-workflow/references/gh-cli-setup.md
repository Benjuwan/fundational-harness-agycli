# GitHub CLI（`gh`）の導入・認証・動作確認 (gh CLI Setup)
ユーザー環境（グローバル・ホスト環境含む）に `gh` が未導入・未認証だった場合に参照する手順です。PR の作成（`gh pr create`）と CI の確認（`gh pr checks`）に `gh` を使います（MCP は使いません）。

- 導入（インストール）と認証は、**ユーザーが行う**作業です。AI はコマンドを案内し、結果を `gh auth status` で確認します。

## 0. 禁止事項（絶対厳守）
| 禁止する操作 | 理由 |
|---|---|
| `gh auth token` | 公式マニュアル：「認証トークンを出力する」コマンド。トークンが会話ログに残る |
| `gh auth status --show-token`（`-t`） | 公式マニュアル：「認証トークンを表示する」オプション。`--json` と併用しても平文のトークンが出力される |
| `~/.config/gh/` の読み取り（`cat`・ファイル閲覧ツールなど） | gh の設定ディレクトリ（公式：既定は `$HOME/.config/gh`。Windows では `$AppData/GitHub CLI`）。認証情報が平文で保存されている場合がある（`security-guidelines.md` 対象2）。存在確認（`ls`）のみ可 |
| `gh auth login --insecure-storage` の案内 | 公式マニュアル：認証情報を認証情報ストアではなく平文で保存するオプション |

- トークンの値をユーザーに貼り付けてもらう、環境変数として表示する、といった操作も行わない。万一コマンド出力にトークンが含まれた場合は `[REDACTED]` に置き換えて報告する（`security-guidelines.md` 対象4）。

## 1. 導入状況の確認
```bash
gh --version
```
- コマンドが見つからない場合は 2 の手順をユーザーに案内する。

## 2. インストール手順
### 2-1. macOS（Homebrew。公式）
```bash
brew install gh
```
- 更新する場合：`brew upgrade gh`
- Homebrew が無い場合は、公式のリリースページ（https://github.com/cli/cli/releases ）にあるビルド済みのバイナリ・インストーラを使う。なお公式ドキュメントには、macOS の `.pkg` インストーラは現在署名されていない旨の注記がある。

### 2-2. Windows（WinGet。公式）
```powershell
winget install --id GitHub.cli --source winget
```
- 更新する場合：`winget upgrade --id GitHub.cli --source winget`
- **インストール後は、ターミナルの新しいウィンドウを開く**（インストーラが PATH を変更するため。公式ドキュメントでは、Windows Terminal では新しいタブを開くだけでは反映されないとしている）。
- WinGet が使えない場合は、公式のリリースページにある `exe` / `msi` を使う。
- Chocolatey・Scoop などは公式ドキュメントで「コミュニティによる非公式の手段」と位置付けられているため、本リファレンスでは案内しない（ユーザーが既に使っている場合を除く）。

## 3. 認証（ユーザーが実行する）
ユーザーに、プロンプト入力欄で以下を実行してもらう（`!` プレフィックスによる手動実行）。
```
! gh auth login
```
- 公式マニュアル：引数なしで実行すると対話形式のセットアップが始まり、既定はブラウザで認証する方式。
- 対話の中で、ホスト（通常は `github.com`）と、git の操作に使うプロトコル（`https` / `ssh`）を選ぶ。どちらを選ぶかはユーザーの普段の運用に合わせる（AI が決めない）。
- 公式マニュアル：認証後、トークンは**システムの認証情報ストア**（macOS ではキーチェーン）に保存される。認証情報ストアが使えない場合は、平文のファイルに保存される。
- `!` で実行できない（対話形式の入力が進まない・エラーになる）場合やワンタイムコードがプロンプト結果欄に表示されない場合は、**ユーザーに別のターミナル（macOS：ターミナル.app など、Windows：PowerShell など）を手動で起動してもらい**、そこで `gh auth login` を実行するよう案内する。出力ログ等からワンタイムコードと URL（https://github.com/login/device）が確認できた場合は速やかにユーザーに伝える。認証完了の報告を受けたら、4 の `gh auth status` で認証状態を確認する。

## 4. 動作確認
```bash
gh auth status
```
- 公式マニュアル：どのホストのどのアカウントで認証されているかを表示する。認証に問題がある場合は、終了コード 1 でエラーを標準エラー出力に出す（`--json` を付けた場合は、致命的なエラー以外は常に終了コード 0）。
- 特定のホストだけを確認する場合：`gh auth status --hostname github.com`
- 確認結果（バージョン、認証済みのホストとアカウント名のみ）を、呼び出し元のスキルや作業の完了報告に「`gh` の導入・認証状況」として記載する。

## 5. 既知の制約：サンドボックス内での認証失敗
- サンドボックス内では、`api.github.com` への通信が拒否され、`gh` が「未認証」と判定されることがある（キーチェーンは読める）。その場合は回避策を試さず、サンドボックスのバイパス許可をユーザーに確認し、コマンド単位で実行する（`destructive-operations.md` 3 の事前確認対象）。

## 参照した一次情報
- macOS のインストール：https://github.com/cli/cli/blob/trunk/docs/install_macos.md
- Windows のインストール：https://github.com/cli/cli/blob/trunk/docs/install_windows.md
- `gh auth login`：https://cli.github.com/manual/gh_auth_login
- `gh auth status`：https://cli.github.com/manual/gh_auth_status
- `gh auth token`：https://cli.github.com/manual/gh_auth_token
- 設定ディレクトリ（`GH_CONFIG_DIR`）：https://cli.github.com/manual/gh_help_environment
