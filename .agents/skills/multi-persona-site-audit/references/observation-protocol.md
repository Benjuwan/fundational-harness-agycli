# 観測プロトコル（証拠接地の作法）

本ファイルは、[SKILL.md](../SKILL.md) 2「証拠接地（事実ベース）」の実務版です。各ペルソナ・サブエージェントは本プロトコルに従い、「感想」ではなく「証拠」を持ち帰ること。

---

## 1. 接地（事実ベース）か、非接地（推測）かの線引き

| 区分 | 例 | 扱い |
|---|---|---|
| **接地できる（証拠必須）** | リンク切れ・404・操作フローの詰まり・レスポンシブ崩れ・コントラスト不足・見出し階層の乱れ・alt/ARIA欠落・コンソールエラー・重いリソース・CTAの発見しにくさ（クリック数） | **本体の指摘**。SS/DOM/操作ログのいずれかで裏取りする |
| **接地できない（推測）** | 「不安を感じる」「魅力的」「離脱しそう」「この層はこう考える」等の感情・心理・購買行動の断定 | 出してよいが **指摘単位で免責ラベルを付す**（4） |

> [!CAUTION]
> 免責ラベルは「接地不能な推測」に効かせる安全網であり、**接地可能な指摘を証拠なしで済ませる免罪符ではない**（＝おためごかしの禁止）。接地できる指摘に証拠を付けずに提出してはならない。

---

## 2. 証拠の種類と取得手段（`playwright-mcp`使用）

ブラウザ操作は `playwright-mcp`（Playwright系ツール）を用いる。**自己流スクリプト（車輪の再発明）は禁止**。以下は代表的な取得手段の対応表。

| 証拠 | 取得手段（MCPツール） |
|---|---|
| 画面の見た目・崩れ | `browser_take_screenshot(filename: "...", scale: "css")`（PC/モバイル両方）。要素単体は `target: "<ref>"` |
| UI構造・要素の存在/ラベル | `browser_snapshot`（アクセシビリティツリー・refs付き）／`browser_find(query: "テキスト")` で該当ノード抽出 |
| ビューポート切替・リサイズ | `browser_resize(width: 1440, height: 900)`（PC）／`browser_resize(width: 390, height: 844)`（モバイル）<br>※後述の「リサイズ処理の検知・反映プロトコル」を必ず遵守すること |
| 遷移・操作フロー | `browser_navigate(url: "...")` / `browser_click(target: "<ref>")` / `browser_press_key` / スクロール等。各ステップのスナップショット/SSを記録 |
| コンソールエラー | `browser_console_messages(level: "warning")` または `level: "error"` |
| ネットワーク（重いリソース・失敗） | `browser_network_requests(static: true)` / `browser_network_request(request_id: ...)` |
| 属性（id/class/data-*/alt/aria） | `browser_evaluate(function: "() => document.querySelector('...').getAttribute('alt')")` 等（snapshotに出ない詳細属性の確認） |
| メタ情報（title/description/OGP） | `browser_evaluate(function: "() => ({ title: document.title, ogTitle: document.querySelector('meta[property=\"og:title\"]')?.content })")` |
| コントラスト比 | `browser_evaluate` で対象要素の前景色・背景色（`getComputedStyle`）を取得し、WCAG のコントラスト比計算式で算出する（`browser_evaluate` 経由の算出を標準手段とする＝これは車輪の再発明にあたらない正規手段） |
| フォーカス移動・順序 | `browser_press_key(key: "Tab")` / `browser_press_key(key: "Shift+Tab")` でフォーカス移動し、`browser_evaluate(function: "() => document.activeElement.outerHTML")` または `browser_snapshot` で確認。到達可否・順序を記録 |
| アクセシビリティツリー | `browser_snapshot`（アクセシブルな役割/名前/refsを含む）を取得 |

> [!NOTE]
> スクリーンショットの `filename` は必ず作業ディレクトリ配下（**`tasks/[サイト名]-audit-report/`** 配下限定）に保存すること。保存先は Artifact ログに追記する。また、`scale` 引数には一貫性保持のため `"css"` を指定することを推奨する。
> ※Artifact ログ自体のパス（`tasks/[サイト名]-audit-report/[CurrentSessionName]_[SubagentName]_ARTIFACTS.md`）は `subagent-policy.md` 7-1 の規約に準拠する（本スキルからは変更しない）。

### リサイズ処理の検知・反映プロトコル（必須遵守）

`browser_resize` を実行した際、CSSメディアクエリのブレークポイント適用やJavaScriptのリサイズイベント（`window.addEventListener('resize', ...)`）、コンポーネントの再レンダリングにわずかな遅延が生じる場合があります。そのため以下の手順を厳守してください:

1. **即時スクリーンショットの禁止**: `browser_resize` 実行直後に即座に `browser_take_screenshot` を呼び出してはならない。
2. **DOM・レイアウト更新の検知（`browser_snapshot` の再取得）**: リサイズ後は必ず `browser_snapshot` を実行し、ハンバーガーメニューの出現や要素配置などのレスポンシブ適用・DOM更新を検知・確認する。
3. **ref番号の再取得**: ビューポート変更に伴い要素の構造や ref 番号が変化するため、リサイズ前の古い ref 番号は破棄し、**リサイズ後に新しく取得した `browser_snapshot` の ref / target を使用** すること。

### セッションのリセット（各ペルソナ開始時に必ず実施）

前ペルソナの状態（Cookie／ログイン／localStorage／スクロール位置）を持ち越さないこと。`playwright-mcp` では以下いずれかの実手段でリセットする（「新規コンテキスト」の具体化）。

- **推奨**: 前ペルソナ終了時に `browser_close` を実行し、次ペルソナ開始時に `browser_navigate(url: "<開始URL>")` を呼び出す（新規クリーンコンテキストで起動＝状態を持ち越さない）。
- **同一セッションを使い回す場合**: `browser_evaluate(function: "() => { localStorage.clear(); sessionStorage.clear(); }")` を実行後、`browser_navigate(url: "<開始URL>")` で再訪する。

---

## 3. アクセシビリティの接地点（機械的事実に限定）

アクセシビリティ指摘は **機械的に検証できる事実に限定** する。以下は接地事実／推測の区別。

- **接地事実**: アクセシビリティツリー／`role`・`aria-*` 属性の有無／コントラスト比の実測値／キーボード操作（Tab/Enter）での到達可否／フォーカス順序／見出し階層／画像alt／フォームラベルの有無。
- **推測（要免責ラベル）**: 「スクリーンリーダー利用者はこう感じる/迷う」といった体験の感想。

---

## 4. 免責ラベルの付与基準

推測を含む指摘には、その **指摘単位** で以下いずれかの注記を付す（レポート統合時にも保持する）。

- 記法例: `【推論】この文言は潜在層に不安を与える可能性がある（実データではない／改善仮説として提示）`
- 競合ベンチの役割演技ペルソナでは、**「対象サイトの観測」は接地事実**、**「競合ならどう攻めるか」の戦略的解釈は推測** として後者にラベルを付す（[persona-scenarios.md](persona-scenarios.md) 4）。

レポート全体には、[report-format.md](report-format.md) の **固定免責文** を別途挿入する（指摘単位ラベルとは別に、全体の安全網として必ず入れる）。

---

## 5. 安全制約（観測時）

- **CV関連ページ（問い合わせ／会員登録／カート／決済／その他あらゆる状態変更を伴う送信フォーム）は閲覧のみ**。遷移・スクロール・スクリーンショットは可。**入力・送信・カート追加などサーバ/セッションの状態を変える操作は行わない**。
- **操作可否の線引き**: サーバ状態を変えない **冪等な操作（検索キーワード入力・絞り込みGET・並び替え・ページャ）は操作可**。一方、登録・決済・問い合わせ送信・カート追加・お気に入り登録など **状態変更を伴う送信は不可**（複雑導線ペルソナでも同様）。判断に迷う場合は「操作しない」を選ぶ。
  - ※ここでの「入力可」は検索ボックス等への GET クエリ入力を指し、**CV関連フォームへの入力・送信（状態変更）とは別物**である。判断に迷う場合は操作しない。
- フォーム入力時バリデーションUXやカート/決済フローのUX等が得られないのは **許容損失**。指摘できない領域があった場合は、その旨を成果物に明記する（黙って省略しない）。フォームの見た目や項目数の多さによるユーザーストレスの推察に留める。

---

## 6. 各ペルソナの持ち帰り成果物（最小セット）

1. 実行したタスクの手順ログ（開始URL → 操作 → 到達/詰まり）。
2. 各指摘に紐づく証拠（スクリーンショットのファイルパス／DOM抜粋／ログ抜粋のいずれか）。
3. 接地できなかった推測には免責ラベル。
4. Artifact ログ（`tasks/[サイト名]-audit-report/[CurrentSessionName]_[SubagentName]_ARTIFACTS.md`）への成果物・スクリーンショット保存先・操作ページ一覧の追記。
