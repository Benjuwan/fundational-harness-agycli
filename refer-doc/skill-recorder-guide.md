# Microsoft Skill Recorder リファレンスガイド 〜 PC操作録画からの業務棚卸し・言語化・AIスキル化〜
本書は、PC画面での操作録画と音声解説から定型業務を言語化し、AIエージェント用スキル（`SKILL.md`）や業務マニュアルへ変換するオープンソースツール **[`microsoft/skill-recorder`](https://github.com/microsoft/skill-recorder)** の概要、仕組み、インストール・起動方法、詳細な使用手順、および利用上の注意点をまとめたリファレンスドキュメントです。

## 1. 概要・コンセプト

### 1-1. 業務棚卸し・言語化スキルの目的
AI利活用による個人の業務効率化を推進するにあたり、最大の問題となるのが**「各個人が普段行っている業務の言語化・構造化（棚卸し）の負担の大きさ」**と**「言語化精度の個人差」**です。  
[`microsoft/skill-recorder`](https://github.com/microsoft/skill-recorder) は、**「普段の業務を一度録画・実況解説するだけで、AIがその意図と手順を理解し、再利用可能なスキル（`SKILL.md`）へ自動変換する」** というアプローチによって、この課題を解決します。

### 1-2. 主な特徴
- **画面録画 ＋ 音声実況（ナレーション）の同時収集:** 単なるマウス操作のキャプチャだけでなく、ユーザーが口頭で解説した音声もキャプチャします。
- **ローカルファースト処理:** 録画・画面フレーム抽出・音声文字起こし（Whisper）はすべてユーザーのローカルPC上で行われます。
- **AI（GitHub Copilot）による言語化:** 録画データ・イベントログ・音声テキストから、業務の「意図（Intent）」と「順序立てられた手順（Steps）」を自動構築します。
- **単なるRPA（操作再生）ではないスキル化:** UIの絶対座標を連打するマクロではなく、`gh` CLIやWeb API、検索ツール（`web_fetch`, `Grep` 等）などAIエージェントが自律的に実行可能な汎用形式（`SKILL.md`）として書き出します。

## 2. 仕組みとアーキテクチャ
[`microsoft/skill-recorder`](https://github.com/microsoft/skill-recorder) は、ローカルで動く Electron デスクトップアプリケーションと、バックエンドで動作する GitHub Copilot CLI によって構成されています。

```
[ ユーザーの業務操作 & ナレーション ]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ ローカルPC処理 (Electron アプリ)                         │
│  ├─ 画面・ウィンドウ・URLキャプチャ                      │
│  ├─ 低頻度の画面静止画（スナップショット）抽出           │
│  └─ 音声文字起こし (ローカル Whisper モデル / 252MB)     │
└────────────────────────────────────────────────────────┘
          │ 「Analyze」実行時のみ送信
          ▼
┌────────────────────────────────────────────────────────┐
│ AI処理 (GitHub Copilot CLI)                            │
│  └─ 意図（Intent）と手順（Steps）の構造化・言語化       │
└────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ 成果物 (再利用可能なアセット)                          │
│  ├─ SKILL.md (AIエージェント用スキル定義 / マニュアル)   │
│  └─ Scheduled Automation (自動実行設定)                │
└────────────────────────────────────────────────────────┘
```

## 3. インストールとアプリ起動手順

### 3-1. インストール形態・動作イメージ
本ツールはCLIからコマンド1行でビルド・登録されますが、**日常的な使い勝手はグローバルインストールされた単体デスクトップアプリそのもの**です。

- **操作感:** インストール後はMacの「アプリケーション」フォルダやSpotlight、Windowsの「スタートメニュー」から通常アプリとして起動可能。
- **安全設計:** 一般的な `npm install -g` 等とは異なり、管理者権限（`sudo`）を使わずにユーザー領域（`~/Applications` や `~/.skill-recorder` など）内に閉じて配置されるため、システム環境を汚しません。

### 3-2. 前提条件
- **GitHub アカウント:** GitHub Copilot へのアクセス権限があるアカウント（無料枠 Copilot Free でも可）。

### 3-3. 🍎 macOS での手順

#### インストールコマンド
ターミナル（Terminal.app）を開き、以下のワンライナーコマンドを実行します。

```bash
commit="32fd0b57e02c3ea1e016cca0d64e59052e93a9b9"; curl -fsSL "https://raw.githubusercontent.com/microsoft/skill-recorder/$commit/install.sh" | SKILL_RECORDER_COMMIT="$commit" SKILL_RECORDER_DETACHED=1 bash
```

> [!NOTE]
> **※ `commit="..."` について:**  
> 本スクリプトはセキュリティおよびビルドの再現性を保つため、40桁のコミットハッシュ（SHA）指定が必須となっています。上記は Release 0.3.1 のコミットハッシュです。

#### アプリ起動と初期設定
1. **アプリの起動:** Spotlight（`Cmd + Space`）または Launchpad / Finder の `~/Applications`（ホームディレクトリ内のアプリケーション）から **「Skill Recorder (Source)」** を起動します。
2. **画面収録の許可設定 (初回のみ):**
   macOS から画面アクセス許可を求められます。「`システム設定 ＞ プライバシーとセキュリティ ＞ 画面収録`」を開き、「Skill Recorder (Source)」の権限をオンに設定してください。
3. **GitHub サインイン:**
   アプリ起動後、表示される案内に従って GitHub アカウントでサインイン（Copilot 認証）を行います。

### 3-4. 🪟 Windows OS での手順

#### 前提条件
- **Windows 11**（x64 または ARM64）

#### インストールコマンド
PowerShell を開き、以下のコマンドを実行します。

```powershell
$commit="32fd0b57e02c3ea1e016cca0d64e59052e93a9b9"; $env:SKILL_RECORDER_COMMIT=$commit; irm "https://raw.githubusercontent.com/microsoft/skill-recorder/$commit/install.ps1" | iex
```

> [!NOTE]
> **※ `commit="..."` について:**  
> 本スクリプトはセキュリティおよびビルドの再現性を保つため、40桁のコミットハッシュ（SHA）指定が必須となっています。上記は Release 0.3.1 のコミットハッシュです。

#### アプリ起動と初期設定
1. **アプリの起動:**
   デスクトップまたはスタートメニューに追加された **「Skill Recorder (Source)」** のショートカットをダブルクリックして起動します。
2. **GitHub サインイン:**
   初回利用時（または最初の「Analyze」実行時）に画面の指示に従い、GitHub アカウントでサインインします。

### 3-5. インストール先ディレクトリと保存データの詳細場所

> [!NOTE]
> ※本項の細かなフォルダ使い分け（`SkillRecorder` と `skill-recorder` など）は、公式の INSTALL.md には詳述されていませんが、実際のインストール時の実挙動（v0.3.1 時点）に基づいた正確な情報です。

管理者権限を使用せず、ユーザーのホームディレクトリ内に配置されます。

#### 🍎 macOS での配置場所
- **アプリ起動パッケージ (.app):**
  `~/Applications/Skill Recorder (Source).app`
  （Spotlight / Launchpad から起動される実体）
- **本体・ランタイムフォルダ (`~/Library/Application Support/SkillRecorder` - PascalCase):**
  - `.../runtime/`: 自動インストールされたポータブル版 Node.js 24 ランタイム
  - `.../versions/`: ビルドされた Skill Recorder のプログラム本体および `node_modules`
- **アプリデータ・キャッシュフォルダ (`~/Library/Application Support/skill-recorder` - kebab-case):**
  - Electron アプリが動的に作成・使用するユーザー設定、ローカルにダウンロードされた Whisper 音声認識モデル (`~252MB`)、録画ログ、セッションキャッシュデータ領域

> [!TIP]
> **2つのフォルダ表記（差異）の使い分け:**  
> - **`SkillRecorder` (PascalCase / 大文字混じり):** インストーラーが構築した**本体プログラム・ポータブル Node.js ランタイム基盤**
> - **`skill-recorder` (kebab-case / 小文字ハイフン):** Electron アプリの起動・録画に伴う**ユーザー設定・アプリデータ・Whisper音声モデル（~252MB）・ログキャッシュの保存領域**

#### 🪟 Windows 11 での配置場所
- **本体・ランタイム (`%LOCALAPPDATA%\SkillRecorder\` - PascalCase):**
  - `...\runtime\`: ポータブル Node.js 24 ランタイム
  - `...\versions\`: ビルドされたプログラム本体
- **アプリデータ・キャッシュ (`%APPDATA%\skill-recorder\` - kebab-case):**
  - ユーザー設定、Whisper 音声モデル（~252MB）、セッションキャッシュデータ
- **ショートカット:**
  - スタートメニュー: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Skill Recorder (Source).lnk`
  - デスクトップ: `C:\Users\<ユーザー名>\Desktop\Skill Recorder (Source).lnk`

#### 手動アンインストール（完全削除）手順
本アプリを削除したい場合は、以下のフォルダ・ファイルをゴミ箱に捨てるだけで安全・完全に削除できます。

- **Mac:** `~/Applications/Skill Recorder (Source).app` および `~/Library/Application Support/` 内の `SkillRecorder` と `skill-recorder` フォルダ
- **Windows:** `%LOCALAPPDATA%\SkillRecorder` と `%APPDATA%\skill-recorder` フォルダ、およびショートカットファイル

### 3-6. バージョン更新（アップデート）方法
新機能がリリースされた場合は、[GitHub リポジトリのリリースページ](https://github.com/microsoft/skill-recorder/releases/latest) から最新バージョンのインストールコマンド（40桁のコミットハッシュが含まれたもの）をコピーし、ターミナル等で再実行することで最新版にアップデートできます。

## 4. 詳細な使用方法と実践ワークフロー（ステップバイステップ）

### 4-1. 録画の開始と停止
- **ショートカットキー:** **`⌘ + Shift + R` (Mac)** / **`Ctrl + Shift + R` (Windows)** を押すと、画面上のどこからでも即座に録画が開始されます。
- **UIボタン:** アプリ画面上の「🔴 Record」ボタンを押して開始することも可能です。

### 4-2. 録画中のコントロール（オーバーレイバー）
録画中は画面上に最前面表示のコントロールバーが現れます。

- **マイク切替・ミュート:** ナレーション用マイクのオン/オフやマイク入力デバイスを切り替え可能。
- **Discard (破棄):** 操作を間違えた際、確認ダイアログを経てそのテイクを破棄できます。
- **Finish (完了):** 業務操作が終わったら Finish ボタンを押して録画を停止します。

### 4-3. 効果的な録画のコツ（ナレーション実況）
**無言の画面操作だけではAIが判断基準や目的を誤解・見落とす可能性があります。**  
録画中は「今から〇〇の顧客データを抽出するためにシステムAを開きます」「ここは毎月15日締めのデータのみを選択します」といった**声での解説実況を交えて操作すること**が言語化精度を高める最大のコツです。

### 4-4. 解析（Analyze）とステップの編集（CREATE SKILL 画面）
録画停止後、「Analyze」を押すとAIによる解析が行われ、**「CREATE SKILL」画面**が表示されます。

#### ① 基本情報の設定

> [!NOTE]
> ※本項の細かなUI操作（インライン編集や Add step 等）は公式の README には詳述されていませんが、実際のアプリUIに基づいた正確な仕様です。

- **Title (タイトル):** スキルのわかりやすい名称（例: `Open GitHub repo and read a Yahoo! News article`）。
- **Slug (スラグ/ID):** スキルの識別名（例: `open-github-and-yahoo-article`）。
- **Description (説明文):** AIエージェントがユーザーのリクエストとタスクを照合するための概要説明。

#### ② WHAT THE SKILL WILL DO（ステップの確認とカスタマイズ）
録画中の操作と音声から自動構築されたプログラムステップが一覧表示されます。

- **自動抽象化機能:** マウスクリック位置ではなく、`web_fetch` (ページ取得) や `Grep` (テキスト抽出) などのバックエンドツールを使った最適な自動化ロジックへ自動変換されます。
- **インライン編集:** 各ステップのテキストやハイライト表示されているパラメータを直接クリックして手動修正できます。
- **並べ替え・削除:** ステップの順番の入れ替えや不要ステップの削除が可能です。
- **手動ステップの追加 (Add step):** 下部フォームから「タイトル (Title)」と「説明 (Description)」を入力することで、不足している手順を新しく手動追加できます。

### 4-5. 成果物フォーマットの選択（`What do you want to build...?` 画面）
ステップの調整が完了したら、目的の用途に応じて以下の成果物フォーマットを選択します。

> [!NOTE]
> ※表内の「Cowork skill」や「Copilot Studio」は、公式 README には記載がありませんが、実際のアプリUI上の選択肢として存在します。


| 選択肢 | 役割・概要 | 主な用途 |
| :--- | :--- | :--- |
| **Scout skill**<br />*(推奨)* | **オンデマンド型 AIスキル (`SKILL.md`)**<br />タスク指示に応じてAIエージェントが自動照合・呼び出しする汎用スキル。 | **ブラウザ閲覧・情報要約などの一般的な定型業務のスキル化** |
| **Scout automation** | **トリガー/スケジュール実行型**<br />定時実行や特定イベントトリガーで定期動作する自動化ワークフロー。 | 毎日朝の定期レポート作成など全自動化 |
| **Cowork skill** | **Microsoft 365 Copilot (Cowork) 用**<br />M365 Copilot 環境へ組み込んで社内共有するためのエクスポート形式。 | 社内Copilot環境への導入・展開 |
| **Copilot Studio** | **Microsoft Copilot Studio 連携**<br />（現在準備中 / Coming soon） | カスタムコパイロット プラットフォーム連携 |

### 4-6. スキルの保存と流用 (`Export...` / `Add to Scout`)
- **`Export...` ボタン:**  
  生成されたスキル（`SKILL.md` 形式）をローカルPC上の任意のフォルダに書き出して保存します。
- **`Add to Scout` ボタン:**  
  Copilot エージェント環境（Scout）にスキルを直接追加・登録します。
- **活用・流用方法:**
  - **AIエージェントへの読み込ませ:** Antigravity や Claude / ChatGPT などのエージェントスキルとして登録し、自動化させる。
  - **マニュアル流用:** 生成された Markdown ファイルをそのままテキストや PDF 形式に変換し、新人教育・担当替え時の業務マニュアルとして共有する。

## 5. 利用時の注意点・制約事項

### 5-1. 無料枠（GitHub Copilot Free）での利用制限
- **画面録画・音声文字起こし:** ローカル処理のため**無制限・完全無料**。
- **Analyze（解析・言語化）:** 月間 **50 リクエスト** の制限（GitHub Copilot Free のチャットリクエスト月間50回の制限に準じます。詳細は [GitHub Copilot のプラン仕様](https://docs.github.com/ja/copilot/about-github-copilot/subscription-plans-for-github-copilot) をご参照ください）。
- **利用目安:** 上記の制限により、1タスクあたり数回の Analyze 試行を考慮すると、お試し・PoC利用で **月 15〜20 タスク程度** のスキル生成が無料枠での現実的な目安となります（※実利用からの推定値）。日常的・大量の棚卸しを行う場合は Copilot Pro / Business への移行が必要です。

### 5-2. セキュリティ・プライバシー対策
- 録画画面やテキストに、パスワード、APIキー、個人情報、機密情報が含まれないよう注意してください。
- 企業内で機密性の高い業務の棚卸しを行う場合は、データがAIの学習に使用されないことが保証された **GitHub Copilot Business / Enterprise** 契約下で利用することを強く推奨します。

### 5-3. 推奨録画時間（タスクの分割）
- 1つの録画は **「5分〜15分程度」** の1単位のタスクに分割して行うことを推奨します。長すぎる動画はスキルの再利用性が下がり、AIの解析精度にも影響するためです（※公式の推奨値ではなく、実用上の目安です）。

---

*最終更新日: 2026年8月3日*  
*対応バージョン: microsoft/skill-recorder v0.3.1 (Commit: 32fd0b57e02c3ea1e016cca0d64e59052e93a9b9)*
