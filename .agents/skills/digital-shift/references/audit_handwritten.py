#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手書き資料から変換されたMarkdownファイルの機械的品質検査スクリプト
（Python標準ライブラリのみで動作）
"""

import argparse
import os
import re
import sys
from pathlib import Path


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
    lines = content.splitlines()

    errors = []
    warnings = []

    # 1. 基本統計
    char_count = len(content.replace(" ", "").replace("\n", "").replace("\t", ""))
    line_count = len(lines)

    if char_count == 0:
        errors.append("ファイルが空（0文字）です。")
    elif char_count < 20:
        warnings.append(f"文字数が極端に少ない（{char_count}文字）です。抽出漏れの可能性があります。")

    # 2. 判読不能マーキング規約の検出
    pattern_unreadable = re.findall(r"\[判読不能\]", content)
    pattern_to_check = re.findall(r"\[要確認:[^\]]+\]", content)
    pattern_strikethrough = re.findall(r"\[抹消線:[^\]]+\]", content)
    pattern_margin = re.findall(r"\[欄外追記:[^\]]+\]", content)
    pattern_figures = re.findall(r"\[図/イラスト:[^\]]+\]", content)

    # 3. ハルシネーション・体裁崩れの兆候チェック
    # 連続する空行（3行以上）
    if re.search(r"\n{4,}", content):
        warnings.append("過度な連続空行（4行以上の改行）が検出されました。")

    # 閉じられていない特殊タグ
    open_brackets = len(re.findall(r"\[(?!.*\])", content))
    if re.search(r"\[(判読不能|要確認|抹消線|欄外追記|図)[^\]]*$", content, re.MULTILINE):
        errors.append("閉じられていないマーキングタグ（`]` 不足）が存在します。")

    # 4. モード別チェック
    if mode == "structure":
        # 見出しが存在するか
        has_headings = any(line.strip().startswith("#") for line in lines)
        if not has_headings:
            warnings.append("構造化モードですが、見出しタグ（`#`, `##` 等）が見つかりません。")

        # 表の列数不整合チェック（複数テーブルブロックに対応）
        current_table = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                current_table.append(stripped)
            else:
                if current_table:
                    # テーブルブロックの検証
                    header_cols = len([c for c in current_table[0].split("|") if c.strip()])
                    for idx, tl in enumerate(current_table[1:], 2):
                        if tl.replace("-", "").replace(":", "").replace("|", "").strip() == "":
                            continue  # 区切り行
                        cols = len([c for c in tl.split("|") if c.strip()])
                        if cols != header_cols:
                            warnings.append(f"表の列数がヘッダーと一致しない行があります (ヘッダー{header_cols}列 に対し {cols}列: {tl[:30]}...)")
                    current_table = []
        if current_table:
            header_cols = len([c for c in current_table[0].split("|") if c.strip()])
            for idx, tl in enumerate(current_table[1:], 2):
                if tl.replace("-", "").replace(":", "").replace("|", "").strip() == "":
                    continue
                cols = len([c for c in tl.split("|") if c.strip()])
                if cols != header_cols:
                    warnings.append(f"表の列数がヘッダーと一致しない行があります (ヘッダー{header_cols}列 に対し {cols}列: {tl[:30]}...)")

    stats = {
        "char_count": char_count,
        "line_count": line_count,
        "unreadable_count": len(pattern_unreadable),
        "to_check_count": len(pattern_to_check),
        "to_check_items": pattern_to_check,
        "strikethrough_count": len(pattern_strikethrough),
        "margin_count": len(pattern_margin),
        "figure_count": len(pattern_figures),
    }

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")

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
    parser.add_argument("--mode", default="raw", choices=["raw", "structure"], help="検査モード (raw / structure)")
    parser.add_argument("--output-report", help="検査レポート（Markdown）の出力先パス（任意）")

    args = parser.parse_args()
    target_path = Path(args.target)

    targets = []
    if target_path.is_file():
        targets.append(target_path)
    elif target_path.is_dir():
        targets = sorted(list(target_path.glob("*.md")))
    else:
        print(f"[ERROR] 対象パスが存在しません: {args.target}")
        sys.exit(1)

    print(f"[*] Markdown機械的品質検査を開始します (Mode={args.mode}, 対象: {len(targets)} ファイル)...")

    results = []
    total_errors = 0
    total_warnings = 0

    for t in targets:
        res = audit_markdown_file(str(t), mode=args.mode)
        results.append(res)
        total_errors += len(res["errors"])
        total_warnings += len(res["warnings"])

        status_badge = f"[{res['status']}]"
        print(f"\n{status_badge} {Path(res['file']).name}")
        print(f"    - 文字数: {res['stats'].get('char_count', 0)} / 行数: {res['stats'].get('line_count', 0)}")
        print(f"    - 判読不能: {res['stats'].get('unreadable_count', 0)} 件 / 要確認: {res['stats'].get('to_check_count', 0)} 件")

        if res["errors"]:
            for err in res["errors"]:
                print(f"    [ERROR] {err}")
        if res["warnings"]:
            for warn in res["warnings"]:
                print(f"    [WARN]  {warn}")

    print("\n" + "=" * 50)
    print(f"[*] 検査完了: 総ファイル数={len(targets)}, エラー={total_errors}, 警告={total_warnings}")
    print("=" * 50)

    # レポート出力
    if args.output_report:
        report_path = Path(args.output_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_lines = [
            f"# 機械的品質検査レポート（Handwritten MD Audit Report）",
            f"- **対象ディレクトリ/ファイル**: `{target_path}`",
            f"- **検査モード**: `{args.mode}`",
            f"- **総ファイル数**: {len(targets)}",
            f"- **判定**: {'FAIL' if total_errors > 0 else ('WARN' if total_warnings > 0 else 'PASS')}",
            f"\n## ファイル別詳細\n",
        ]
        for r in results:
            fname = Path(r["file"]).name
            report_lines.append(f"### `{fname}` [{r['status']}]")
            report_lines.append(f"- 文字数: {r['stats'].get('char_count', 0)} / 行数: {r['stats'].get('line_count', 0)}")
            report_lines.append(f"- 判読不能: {r['stats'].get('unreadable_count', 0)} 件 / 要確認: {r['stats'].get('to_check_count', 0)} 件 / 抹消線: {r['stats'].get('strikethrough_count', 0)} 件 / 欄外追記: {r['stats'].get('margin_count', 0)} 件")
            if r["stats"].get("to_check_items"):
                report_lines.append(f"- 要確認一覧: {', '.join(r['stats']['to_check_items'])}")
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
