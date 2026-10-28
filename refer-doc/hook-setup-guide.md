# フック（Hooks）初期設定・運用ガイド
本ドキュメントは、AIアシスタント/汎用ハーネス環境において、AIの安全な自律動作・事前承認プロセス（HITL）の強制、および記憶の風化防止を実現するためのフック初期設定および運用ガイドです。

## 1. フックの概要と同梱スクリプト

### フック（Hooks）とは
Antigravity CLI の実行ループ（モデル呼び出し前、ツール実行前など）の特定タイミングで、自動的にカスタムスクリプトを実行する仕組みです。

### 本環境で利用するフック機能と同梱スクリプト (`.agents/hooks/` 配下)

| スクリプト名 | タイミング (イベント) | 目的・機能 |
| :--- | :--- | :--- |
| **`pre-invocation-inject.py`** | `PreInvocation` (プロンプト送信直前) | コンテキストの自動圧縮発生時に、`workflow.md` などの最優先ルールをプロンプト直前に動的再注入し、ルールの形骸化を防ぎます。 |
| **`checkpoint-alert-inject.py`** | `PreInvocation` (プロンプト送信直前) | 会話ログからコンテキスト圧縮を検知し、ユーザーへ新しいセッション（チャット）への引き継ぎ切替を促す警告を出力します。 |
| **`checkpoint_utils.py`** | - | 会話ログ管理を行う共通ユーティリティ（上記スクリプトから参照）。 |

## 2. フックの登録（ワークスペース設定 `.agents/hooks.json`）
同梱スクリプトは、ワークスペース設定の **`.agents/hooks.json`** で登録済みです（同梱済み）。  
フック実行時の作業ディレクトリは `hooks.json` のあるディレクトリ（`.agents/`）になるため、スクリプトは **`./hooks/...` の相対パス** で指定しています。

- **Mac / Linux**: `python3 ./hooks/スクリプト名.py`（同梱の設定のまま使えます）
- **Windows**: `python ./hooks/スクリプト名.py`（`.agents/hooks.json` の `python3` を `python` に書き換えてください）

> [!NOTE]
> このドキュメントをAIに参照させて「希望する機能（フック）が実現可能かどうかを判断及び、スクリプトの作成から登録までを任せる」と良いでしょう。  
> 自作のフックを追加する場合は、スクリプトを `.agents/hooks/` に置き、`.agents/hooks.json` に追記してください。CLIを再起動することで、設定が有効化されます。

## 3. （参考）設定ファイル（`hooks.json`）の配置場所と優先順位
`hooks.json` のトップレベルのキーはフック名で、その中にイベント（`PreInvocation` など）を記述します。

> [!IMPORTANT]
> - **配置場所**: ワークスペースの `.agents/hooks.json`（本リポジトリ標準）と、グローバル設定の両方に対応しています。
>   - **グローバル（Windows）**: `C:/Users/ユーザー名/.gemini/config/hooks.json`
>   - **グローバル（Mac / Linux）**: `/Users/ユーザー名/.gemini/config/hooks.json`
> - **グローバル設定の場合**: 作業ディレクトリが `~/.gemini/config/` になるため、スクリプトは **絶対パス** で指定します（例：`python3 /絶対パス/.agents/hooks/スクリプト名.py`、Windows は `python C:/絶対パス/.agents/hooks/スクリプト名.py`）。
> - **同名のフック**: ワークスペースとグローバルで同じ名前のフックがある場合は、**ワークスペース側が優先** されます（別名のフックはマージされて順に実行されます）。
> - ※旧版のCLIでは、フォルダを信頼したあとにワークスペースの `.agents/hooks.json` が読み込まれない不具合がありました（公式の変更履歴で修正済み）。

<details>
<summary><b>同梱の <code>.agents/hooks.json</code> の内容（クリックで展開）</b></summary>
※ Windows 環境の場合は `python3` を `python` に変更してください。

```json
{
  "pre-invocation-inject": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python3 ./hooks/pre-invocation-inject.py",
        "timeout": 5
      }
    ]
  },
  "checkpoint-alert-inject": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python3 ./hooks/checkpoint-alert-inject.py",
        "timeout": 5
      }
    ]
  }
}
```

</details>
