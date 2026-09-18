"""
手書き資料から変換されたMarkdownファイルの機械的品質検査スクリプト
（Python標準ライブラリのみで動作）
"""

import argparse
import re
import sys
from pathlib import Path


def _count_columns(row: str) -> int:
    """Markdownテーブルの1行から列数（セルの個数）を返す。

    `| 名前 | 年齢 | 所属 |` ->
    `["", " 名前 ", " 年齢 ", " 所属 ", ""]` ->
    `[" 名前 ", " 年齢 ", " 所属 "]`（先頭と末尾の空要素を [1:-1] で除外するため）
    となって、結果は3が返る
    """
    return len(row.split("|")[1:-1])


# マーキングタグの開始検出パターン（種別名をグループ1で取得する）
_MARKER_START_RE = re.compile(r"\[(判読不能|要確認|抹消線|欄外追記|図)")

# 閉じたマーカー全文が、種別ごとの正規の書式を満たすかどうかの判定パターン
_MARKER_VALID_RE = {
    "判読不能": re.compile(r"^\[判読不能(\]|:)"),
    "要確認": re.compile(r"^\[要確認:"),
    "抹消線": re.compile(r"^\[抹消線:"),
    "欄外追記": re.compile(r"^\[欄外追記:"),
    # 実運用では `[図:` が多数派のため、`[図/イラスト:` と併せて両表記を拾う
    "図": re.compile(r"^\[図(?:/イラスト)?:"),
}


def _scan_markers(content: str) -> tuple[dict[str, list[str]], list[str]]:
    """本文中のマーキングタグをブラケット深度で走査する。

    `[<種別>` を見つけた位置から `[` で +1 / `]` で −1 と深度を数え、深度が 0 に
    戻った位置を閉じ位置とみなす。**改行をまたいで走査する**ため、原本の改行を
    忠実に再現した複数行マーカー（raw モードでは正常系）を未閉じと誤検知しない。
    深度が 0 に戻らないままファイル末尾へ到達したものだけを「未閉じ」と判定する。

    戻り値は `(種別ごとの閉じたマーカー全文のリスト, 未閉じ箇所の説明リスト)`。
    """
    closed: dict[str, list[str]] = {kind: [] for kind in _MARKER_VALID_RE}  # 閉じ
    unclosed: list[str] = []  # 未閉じ

    # content から注釈（マーキングタグ: `_MARKER_START_RE`）に該当するものを見つけて繰り返し処理に進む
    for match in _MARKER_START_RE.finditer(content):
        kind = match.group(1)
        # `start`: 正規表現全体が一致した範囲の開始インデックスを返す（今回の場合は`re.compile(r"\[...`の`[`部分の位置）
        start = match.start()

        depth = 0
        close_pos = -1
        # 文章`[`の位置から全文文字列までの繰り返し処理
        for i in range(start, len(content)):
            char = content[i]

            # 開始（例：`[要確認: 文字]`の`[`）
            if char == "[":
                depth += 1

            # 終了（例: `[要確認: 文字]`の`]`）
            elif char == "]":
                depth -= 1
                # 注釈終了時に注釈文字の`]`の文字インデックス（文字位置）に更新して繰り返し処理終了
                if depth == 0:
                    close_pos = i
                    break

        # 未閉じ（`]`）注釈の検出
        if close_pos < 0:
            # 行番号は、開始位置までに現れた改行の数から算出する
            line_no = content.count("\n", 0, start) + 1
            unclosed.append(f"{line_no}行目 [{kind}")
            continue

        # 注釈部分のみ抽出し、注釈種別と抽出した種別が合致するかを判定し、パスすれば当該種別に追加
        marker_text = content[start : close_pos + 1]
        if _MARKER_VALID_RE[kind].match(marker_text):
            closed[kind].append(marker_text)

    return closed, unclosed


def _is_separator_row(row: str) -> bool:
    """Markdownテーブルの区切り行（`|---|:--:|` など）かどうかを判定する"""
    return row.replace("-", "").replace(":", "").replace("|", "").strip() == ""


def _check_table_block(table: list[str], warnings: list[str]) -> None:
    """1つのテーブルブロックの列数整合性を検証し、不一致を warnings に追記する"""
    header_cols = _count_columns(table[0])
    for row in table[1:]:
        if _is_separator_row(row):
            continue
        cols = _count_columns(row)  # 各列のセル数を取得
        if cols != header_cols:
            warnings.append(
                f"表の列数がヘッダーと一致しない行があります (ヘッダー{header_cols}列 に対し {cols}列: {row[:30]}...)"
            )


def audit_markdown_file(file_path: str, mode: str = "raw") -> dict:
    """単一のMarkdownファイルを検査してレポート辞書を返す"""
    path = Path(file_path)
    if not path.exists():
        return {
            "file": str(path),
            "status": "FAIL",
            "errors": [f"ファイルが存在しません: {file_path}"],
            "warnings": [],
            "stats": {},
        }

    content = path.read_text(encoding="utf-8")

    # `splitlines`: 改行コード（`\n`など）で分割してリストを返す
    lines = content.splitlines()

    errors = []
    warnings = []

    # 1. 基本統計（char_count: 文字数と line_count: **空行を含む**文章段落数）
    char_count = len(content.replace(" ", "").replace("\n", "").replace("\t", ""))
    line_count = len(lines)

    if char_count == 0:
        errors.append("ファイルが空（0文字）です。")
    elif char_count < 20:
        warnings.append(
            f"文字数が極端に少ない（{char_count}文字）です。抽出漏れの可能性があります。"
        )

    # 2. 判読不能マーキング規約の検出（件数カウントと未閉じ検出を一元化）
    marker_closed, marker_unclosed = _scan_markers(content)

    # 3. ハルシネーション・体裁崩れの兆候チェック
    # 連続する空行（3行以上）
    if re.search(r"\n{4,}", content):
        warnings.append("過度な連続空行（4行以上の改行）が検出されました。")

    # 閉じられていない特殊タグ（該当箇所を行番号・種別付きで各件列挙する）
    for location in marker_unclosed:
        errors.append(f"閉じられていないマーキングタグ（`]` 不足）: {location}")

    # 4. モード別チェック
    if mode == "structure":
        # 見出しが存在するか（`line`: `content`内のそれぞれの文章段落）
        has_headings = any(line.strip().startswith("#") for line in lines)
        if not has_headings:
            warnings.append(
                "構造化モードですが、見出しタグ（`#`, `##` 等）が見つかりません。"
            )

        # 表の列数不整合チェック（複数テーブルブロックに対応）
        current_table = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                current_table.append(stripped)
            elif current_table:
                # テーブルブロックの終端に到達したので、溜めた行をまとめて検証する
                _check_table_block(current_table, warnings)
                current_table = []

        # ファイル末尾がテーブル行で終わった場合の取りこぼしを検証する
        if current_table:
            _check_table_block(current_table, warnings)

    stats = {
        "char_count": char_count,
        "line_count": line_count,
        "unreadable_count": len(marker_closed["判読不能"]),
        "to_check_count": len(marker_closed["要確認"]),
        "to_check_items": marker_closed["要確認"],
        "strikethrough_count": len(marker_closed["抹消線"]),
        "margin_count": len(marker_closed["欄外追記"]),
        "figure_count": len(marker_closed["図"]),
    }

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")

    # `pathlib.Path.resolve()`: 指定されたパスを「絶対パス」かつ「実際の正しいパス（シンボリックリンクなどを解決した状態）」に変換して返すメソッド
    return {
        "file": str(path.resolve()),
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
    }


def main():
    parser = argparse.ArgumentParser(description="手書き変換Markdownの機械的検査ツール")
    parser.add_argument("target", help="検査対象のMarkdownファイルまたはディレクトリ")
    parser.add_argument(
        "--mode",
        default="raw",
        choices=["raw", "structure"],
        help="検査モード (raw / structure)",
    )
    parser.add_argument(
        "--output-report", help="検査レポート（Markdown）の出力先パス（任意）"
    )

    args = parser.parse_args()
    target_path = Path(args.target)

    targets = []
    if target_path.is_file():
        targets.append(target_path)
    elif target_path.is_dir():
        # 素材ごとにサブディレクトリを分ける規約のため、再帰的に収集する
        targets = sorted(target_path.rglob("*.md"))
    else:
        print(f"[ERROR] 対象パスが存在しません: {args.target}")
        sys.exit(1)

    # 0件のまま検査を進めると「何も検査せずPASS」という誤った結果になるため止める
    if not targets:
        print(f"[ERROR] 検査対象の .md ファイルが見つかりません: {args.target}")
        sys.exit(1)

    print(
        f"[*] Markdown機械的品質検査を開始します (Mode={args.mode}, 対象: {len(targets)} ファイル)..."
    )

    results = []
    total_errors = 0
    total_warnings = 0

    for t in targets:
        res = audit_markdown_file(str(t), mode=args.mode)

        # res: 各マークダウンファイル内の**空行を含む**各文章段落に対して検証を行った当該マークダウンファイル全体の判定結果（辞書形式）
        results.append(res)

        total_errors += len(res["errors"])
        total_warnings += len(res["warnings"])

        status_badge = f"[{res['status']}]"
        print(
            f"\n{status_badge} {Path(res['file']).parent.name}/{Path(res['file']).name}"
        )
        print(
            f"    - 文字数: {res['stats'].get('char_count', 0)} / 行数: {res['stats'].get('line_count', 0)}"
        )
        print(
            f"    - 判読不能: {res['stats'].get('unreadable_count', 0)} 件 / 要確認: {res['stats'].get('to_check_count', 0)} 件"
        )
        print(
            f"    - 抹消線: {res['stats'].get('strikethrough_count', 0)} 件 / 欄外追記: {res['stats'].get('margin_count', 0)} 件 / 図: {res['stats'].get('figure_count', 0)} 件"
        )

        if res["errors"]:
            for err in res["errors"]:
                print(f"    [ERROR] {err}")
        if res["warnings"]:
            for warn in res["warnings"]:
                print(f"    [WARN]  {warn}")

    print("\n" + "=" * 50)
    print(
        f"[*] 検査完了: 総ファイル数={len(targets)}, エラー={total_errors}, 警告={total_warnings}"
    )
    print("=" * 50)

    # レポート出力
    if args.output_report:
        report_path = Path(args.output_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_lines = [
            "# 機械的品質検査レポート（Handwritten MD Audit Report）",
            f"- **対象ディレクトリ/ファイル**: `{target_path}`",
            f"- **検査モード**: `{args.mode}`",
            f"- **総ファイル数**: {len(targets)}",
            f"- **判定**: {'FAIL' if total_errors > 0 else ('WARN' if total_warnings > 0 else 'PASS')}",
            "\n## ファイル別詳細\n",
        ]
        for r in results:
            fname = f"{Path(r['file']).parent.name}/{Path(r['file']).name}"
            report_lines.append(f"### `{fname}` [{r['status']}]")
            report_lines.append(
                f"- 文字数: {r['stats'].get('char_count', 0)} / 行数: {r['stats'].get('line_count', 0)}"
            )
            report_lines.append(
                f"- 判読不能: {r['stats'].get('unreadable_count', 0)} 件 / 要確認: {r['stats'].get('to_check_count', 0)} 件 / 抹消線: {r['stats'].get('strikethrough_count', 0)} 件 / 欄外追記: {r['stats'].get('margin_count', 0)} 件 / 図: {r['stats'].get('figure_count', 0)} 件"
            )
            if r["stats"].get("to_check_items"):
                report_lines.append(
                    f"- 要確認一覧: {', '.join(r['stats']['to_check_items'])}"
                )
            if r["errors"]:
                for e in r["errors"]:
                    report_lines.append(f"- ❌ **エラー**: {e}")
            if r["warnings"]:
                for w in r["warnings"]:
                    report_lines.append(f"- ⚠️ **警告**: {w}")
            report_lines.append("")

        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"[*] レポートを保存しました: {report_path.resolve()}")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
