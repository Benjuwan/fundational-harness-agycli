#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDFファイルをページごとの高解像度画像（PNG/JPG）に一括変換するスクリプト
（pdf2image + Pillow + Poppler を利用）
"""

import argparse
import os
import sys
from pathlib import Path


def convert_pdf_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 300,
    fmt: str = "png",
) -> list[str]:
    """PDFをページごとの画像に変換して保存し、生成されたファイルパスリストを返す"""
    try:
        from pdf2image import convert_from_path
        from PIL import Image
    except ImportError as e:
        print(f"[ERROR] 必要なライブラリが読み込めません: {e}")
        print("仮想環境（.venv）内で実行されているか確認してください。")
        sys.exit(1)

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"[ERROR] 対象PDFが存在しません: {pdf_path}")
        sys.exit(1)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] PDFの読み込みと画像変換を開始します (DPI={dpi}, Format={fmt.upper()})...")
    print(f"    対象PDF: {pdf_file.resolve()}")
    print(f"    出力先 : {out_dir.resolve()}")

    try:
        images: list[Image.Image] = convert_from_path(
            str(pdf_file.resolve()),
            dpi=dpi,
            fmt=fmt.lower(),
        )
    except Exception as e:
        print(f"[ERROR] PDFから画像への変換に失敗しました: {e}")
        print("PopplerがOSにインストールされているか確認してください。")
        sys.exit(1)

    saved_paths = []
    total_pages = len(images)
    print(f"[*] 全 {total_pages} ページの変換完了。画像ファイルを保存中...")

    for idx, img in enumerate(images, 1):
        filename = f"page_{idx:02d}.{fmt.lower()}"
        save_path = out_dir / filename
        img.save(str(save_path), fmt.upper())
        saved_paths.append(str(save_path.resolve()))
        print(f"    - [{idx}/{total_pages}] 保存完了: {save_path.name}")

    print(f"[SUCCESS] すべての画像保存が完了しました（合計 {len(saved_paths)} 枚）。")
    return saved_paths


def main():
    parser = argparse.ArgumentParser(description="PDFを高解像度画像に一括変換するツール")
    parser.add_argument("--pdf", required=True, help="変換対象のPDFファイルパス")
    parser.add_argument("--output-dir", required=True, help="画像の保存先ディレクトリパス")
    parser.add_argument("--dpi", type=int, default=300, help="変換解像度 (デフォルト: 300)")
    parser.add_argument("--format", default="png", choices=["png", "jpg", "jpeg"], help="画像フォーマット (デフォルト: png)")

    args = parser.parse_args()
    convert_pdf_to_images(
        pdf_path=args.pdf,
        output_dir=args.output_dir,
        dpi=args.dpi,
        fmt=args.format,
    )


if __name__ == "__main__":
    main()
