# フック（Hooks）初期設定・運用ガイド
本ドキュメントは、AIアシスタント/汎用ハーネス環境において、AIの安全な自律動作・事前承認プロセス（HITL）の強制、および記憶の風化防止を実現するためのフック初期設定および運用ガイドです。

## 1. フックの概要と同梱スクリプト

### フック（Hooks）とは
Antigravity CLI の実行ループ（モデル呼び出し前、ツール実行前など）の特定タイミングで、自動的にカスタムスクリプトを実行する仕組みです。

### 本環境で利用するフック機能と同梱スクリプト (`.agents/hooks/` 配下)

| スクリプト名 | タイミング (イベント) | 目的・機能 |
| :--- | :--- | :--- |
| **`pre-command-check.py`** | `PreToolUse` (ツール実行直前) | AIが無言でコマンドやサブエージェントを実行しようとした際にブロックし、日本語での事前説明（30文字以上）を強制します。 |
| **`pre-invocation-inject.py`** | `PreInvocation` (プロンプト送信直前) | コンテキストの自動圧縮発生時に、`workflow.md` などの最優先ルールをプロンプト直前に動的再注入し、ルールの形骸化を防ぎます。 |
| **`detect-checkpoint.py`** | `PreInvocation` (プロンプト送信直前) | 会話ログからコンテキスト圧縮を検知し、ユーザーへ新しいセッション（チャット）への引き継ぎ切替を促す警告を出力します。 |
| **`checkpoint_utils.py`** | - | 会話ログ管理を行う共通ユーティリティ（上記スクリプトから参照）。 |

## 2. フックの登録手順（推奨: CLIからの設定）
ナレッジワーカー向けには、Antigravity CLIの `/hooks` コマンドを使用した設定を推奨しています。

1. チャットUIまたはターミナルで **`/hooks`** コマンドを実行します。
2. 登録したいイベント（`PreToolUse` または `PreInvocation`）を選択します。
3. 名称（Name）と実行コマンド（Command）を入力します。
   - **実行コマンドの指定例**:
     - **Mac / Linux**: `python3 /絶対パス/.agents/hooks/スクリプト名.py`
     - **Windows**: `python C:/絶対パス/.agents/hooks/スクリプト名.py`
4. CLIを再起動することで、設定が有効化されます。

## 3. （参考）設定ファイル（`hooks.json`）による一括設定
一括で設定したい場合や設定内容を直接確認したい場合は、グローバルの `hooks.json` を編集します。

> [!IMPORTANT]
> **設定ファイルの配置場所**
> プロジェクト内の `.agents/hooks.json` ではなく、**OSユーザーディレクトリ配下のグローバル設定ファイル**に記述する必要があります。
> - **Windows**: `C:/Users/ユーザー名/.gemini/config/hooks.json`
> - **Mac / Linux**: `/Users/ユーザー名/.gemini/config/hooks.json`

<details>
<summary><b><code>hooks.json</code> 設定テンプレート（クリックで展開）</b></summary>
※ Windows 環境の場合は `python3` を `python` に変更し、パスを `C:/Users/...` 形式に置き換えてください。

```json
{
  "pre-invocation-inject": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python3 /絶対パス/.agents/hooks/pre-invocation-inject.py",
        "timeout": 5
      }
    ]
  },
  "detect-checkpoint": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python3 /絶対パス/.agents/hooks/detect-checkpoint.py",
        "timeout": 5
      }
    ]
  },
  "sandbox-bypass-check": {
    "PreToolUse": [
      {
        "matcher": "run_command",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /絶対パス/.agents/hooks/pre-command-check.py",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "invoke_subagent",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /絶対パス/.agents/hooks/pre-command-check.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

</details>

---

## 4. PreToolUse フック運用時の仕様限界と注意点
PreToolUse フック（ツール実行前制御）を運用する際、CLIシステムの構造上、以下の2点に関する仕様限界と注意点が存在します。

### (1) 評価順序の限界（ユーザー承認プロンプトの先行）
PreToolUse フックに配置したカスタム検証スクリプト（`pre-command-check.py` 等）が判定を実行する前に、CLI システム本体のユーザー承認ダイアログ（`BypassSandbox` などの確認プロンプト）が先に表示されてしまう構造的限界が存在します。そのため、スクリプト側でブロックや事前チェックを行おうとしても、画面上ではシステム側のダイアログ応答が先行して求められる場合があります。

### (2) エラーメッセージの透過上書き問題
フック側のスクリプトが検証失敗としてブロック理由（`reason`）を返したとしても、CLI システム側の標準エラーメッセージ（`user denied permission...` 等）によって透過的に上書きされてしまう場合があります。この上書きが発生すると、AI はフックが指摘した本来のブロック理由（例: 「30文字以上の事前説明が不足している」）を認識できず、エラーの真因を把握して自律的に自己修正することが困難になる場合がある点に留意してください。
