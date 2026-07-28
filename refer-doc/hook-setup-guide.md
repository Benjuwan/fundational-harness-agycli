# フック（Hooks）初期設定・運用ガイド

本ドキュメントは、AIアシスタント/汎用ハーネス環境において、AIの安全な自律動作・HITL（Human-in-the-Loop）の承認プロセス強制、およびコンテキスト忘却防止を実現するためのフック初期設定および運用ガイドです。

---

## 1. フックの概要と導入目的

### フック（Hooks）とは
Antigravity CLI の実行ループ（モデル呼び出し前、ツール実行前、セッション終了時など）の特定のタイミングで、自動的にカスタムスクリプトを実行する仕組みです。

### 導入目的
1. **無言実行・自律暴走の防止（PreToolUse）**: コマンド実行やサブエージェント起動の直前に、AIが「どのような目的で何をしようとしているか」を日本語テキストで事前に説明し、ユーザーの承認（y/n）を求めるステップを強制します。説明がないツール呼び出しは物理的にブロック（deny）されます。
2. **記憶の風化（Lost in the Middle）対策（PreInvocation）**: 会話が長くなりコンテキストが自動圧縮された際、モデル呼び出し直前に最優先ルール（`workflow.md` 等）を自動で動的再注入し、ルールの形骸化を防ぎます。
3. **パフォーマンス低下の警告（detect-checkpoint）**: 会話ログからコンテキスト圧縮を検知し、ユーザーに新しいセッションへの切替（引き継ぎ作成）を促します。

---

## 2. フック設定ファイル（`hooks.json`）の配置とOS別設定

> [!IMPORTANT]
> ### 設定ファイルの配置場所（必須ルール）
> フックを正常に機能させるには、プロジェクトローカルではなく**グローバル（OSユーザーディレクトリ配下）の `hooks.json` に設定を記述する必要があります**。プロジェクト内の `.agents/hooks.json` では機能しません。

### ファイル配置パス
- **Windows OS**: `C:/Users/ユーザー名/.gemini/config/hooks.json`
- **Mac / Linux OS**: `/Users/ユーザー名/.gemini/config/hooks.json`

### パス指定および実行コマンドの書き方
- **OS絶対パス指定**: `hooks.json` 内の `command` フィールドには、スクリプトの配置先を**絶対パス**で指定してください。
- **実行Pythonコマンド**:
  - Windows OS: `python` を使用
  - Mac / Linux OS: `python3` を使用

---

## 3. 設定ファイル（`hooks.json`）の設定例

### 【Windows OS】設定例
```json
{
  "pre-invocation-inject": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python C:/Users/ユーザー名/Desktop/YOUR_PROJECT/.agents/hooks/pre-invocation-inject.py",
        "timeout": 5
      }
    ]
  },
  "detect-checkpoint": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python C:/Users/ユーザー名/Desktop/YOUR_PROJECT/.agents/hooks/detect-checkpoint.py",
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
            "command": "python C:/Users/ユーザー名/Desktop/YOUR_PROJECT/.agents/hooks/pre-command-check.py",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "invoke_subagent",
        "hooks": [
          {
            "type": "command",
            "command": "python C:/Users/ユーザー名/Desktop/YOUR_PROJECT/.agents/hooks/pre-command-check.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### 【Mac / Linux OS】設定例
```json
{
  "pre-invocation-inject": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python3 /Users/ユーザー名/Desktop/YOUR_PROJECT/.agents/hooks/pre-invocation-inject.py",
        "timeout": 5
      }
    ]
  },
  "detect-checkpoint": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python3 /Users/ユーザー名/Desktop/YOUR_PROJECT/.agents/hooks/detect-checkpoint.py",
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
            "command": "python3 /Users/ユーザー名/Desktop/YOUR_PROJECT/.agents/hooks/pre-command-check.py",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "invoke_subagent",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/ユーザー名/Desktop/YOUR_PROJECT/.agents/hooks/pre-command-check.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

---

## 4. フックイベント（発火タイミング）一覧

Antigravity CLI には主に以下の5つのフックタイミングが用意されています。

| イベント名 | 発火タイミング | 主な用途・活用例 |
| :--- | :--- | :--- |
| **`PreInvocation`** | AI（LLM）へプロンプトが送信される直前 | 動的ルール注入（インジェクション）、コンテキスト圧縮の検知 |
| **`PostInvocation`** | AI（LLM）から返答を受け取った直後 | 応答ログの記録・分析、特定キーワードの監視 |
| **`PreToolUse`** | AIがツール（コマンド等）を実行する直前 | コマンド事前説明のチェック、危険なコマンドや無言実行のブロック |
| **`PostToolUse`** | AIがツールの実行を完了した直後 | ログ・実行結果に含まれる機密情報（APIキー等）のマスキング |
| **`Stop`** | セッション終了・CLI中断時 | 一時ファイルの削除やバックグラウンドプロセスのクリーンアップ |

---

## 5. CLI経由（`/hooks` コマンド）での設定手順

1. チャットUIまたはターミナルで `/hooks` コマンドを実行します。
2. 登録したいイベント（`PreInvocation` や `PreToolUse`）を選択します。
3. 名称（Name）と実行コマンド（Command）を入力します。
   - 例: `python3 /Users/ユーザー名/YOUR_PROJECT/.agents/hooks/pre-command-check.py`
4. CLIを再起動することで、グローバルの `hooks.json` に設定が自動反映されます。

---

## 6. 同梱フックスクリプト一覧（`refer-doc/hookfiles/` 配下）

`fundational-harness-agycli/refer-doc/hookfiles/` 配下に格納されている汎用フックスクリプトの概要です。プロジェクトセットアップ時に `.agents/hooks/` へ配置してご活用ください。

1. **`pre-command-check.py`**
   - **機能**: ツール実行と同じターン内でAIによる事前の日本語説明（30文字以上）があるかを判定。説明がない場合はツール実行を拒否（deny）します。
2. **`pre-invocation-inject.py`**
   - **機能**: コンテキストの自動圧縮発生時に、`workflow.md` などの最優先ルールをプロンプト直前に動的注入します。
3. **`detect-checkpoint.py`**
   - **機能**: 会話ログ（`transcript.jsonl`）の行数からコンテキスト圧縮を識別し、AIへ緊急警告メッセージを差し込みます。
4. **`checkpoint_utils.py`**
   - **機能**: 会話ログの行数管理・CHECKPOINTタグ識別を行う共通ユーティリティ関数群です。
