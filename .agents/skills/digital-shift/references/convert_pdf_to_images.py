"""
PDFファイルをページごとの高解像度画像（PNG/JPG）に一括変換するスクリプト
（pdf2image + Pillow + Poppler を利用）
"""

import argparse
import math
import re
import sys
from pathlib import Path


def _resolve_safe_dpi(pdf_path: Path, requested_dpi: int) -> int:
    """Pillowのピクセル数上限を超えない範囲まで DPI を引き下げて返す。

    スマートフォンの撮影画像をそのままPDF化した素材はページサイズ自体が巨大なため、
    高DPIを指定するとピクセル数が Pillow の DecompressionBomb 判定値を超えて変換が失敗する。
    指定DPIで収まる場合、およびページサイズを取得できない場合は指定値をそのまま返す。
    """
    from pdf2image import pdfinfo_from_path
    from PIL import Image

    try:
        page_size = str(pdfinfo_from_path(str(pdf_path)).get("Page size", ""))
    except Exception:
        # ページサイズを取得できない場合は判定を諦め、指定DPIを尊重する
        return requested_dpi

    # page_size の先頭が「数値 x 数値（612 x 792 pts）」の形式に一致するかを正規表現でチェック
    matched = re.match(r"([\d.]+)\s*x\s*([\d.]+)", page_size)
    if not matched:
        return requested_dpi

    # width_pt, height_pt は page_size から抽出したページ幅・高さ（単位: pt）
    # 例: width_pt: 612.0, height_pt: 792.0
    width_pt, height_pt = float(matched.group(1)), float(matched.group(2))
    if width_pt <= 0 or height_pt <= 0:
        return requested_dpi

    # 1pt = 1/72インチ。総ピクセル数 = (width_pt / 72 * dpi) * (height_pt / 72 * dpi)
    max_dpi = int(math.sqrt(Image.MAX_IMAGE_PIXELS * 72 * 72 / (width_pt * height_pt)))
    if max_dpi >= requested_dpi:
        return requested_dpi

    print(
        f"[WARN] ページサイズ {width_pt:.0f} x {height_pt:.0f} pt に対して DPI {requested_dpi} は"
        f"ピクセル数が過大です。DPI {max_dpi} へ自動的に引き下げます。"
    )
    return max_dpi


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

    dpi = _resolve_safe_dpi(pdf_file.resolve(), dpi)

    print(
        f"[*] PDFの読み込みと画像変換を開始します (DPI={dpi}, Format={fmt.upper()})..."  # `fmt.upper()` -> 例: PNG
    )

    # `pathlib.Path.resolve()`: 指定されたパスを「絶対パス」かつ「実際の正しいパス（シンボリックリンクなどを解決した状態）」に変換して返すメソッド
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
        print("考えられる原因:")
        print(
            "  - Poppler が OS にインストールされていない（macOS: brew install poppler）"
        )
        print(
            "  - ページサイズが大きく、指定DPIではピクセル数が過大（--dpi を下げて再実行）"
        )
        sys.exit(1)

    saved_paths = []
    total_pages = len(images)
    print(f"[*] 全 {total_pages} ページの変換完了。画像ファイルを保存中...")

    for idx, img in enumerate(images, 1):
        # `page_001.拡張子（小文字）`の形式。3桁ゼロ埋めにすることで、100ページ超（上限999）でもファイル名の辞書順が崩れない
        filename = f"page_{idx:03d}.{fmt.lower()}"
        # 出力先ディレクトリとファイル名を結合して保存先パスを組み立てる
        save_path = out_dir / filename
        img.save(str(save_path), fmt.upper())
        # 呼び出し元が後続処理で使えるよう、絶対パスに正規化してリストへ追加
        saved_paths.append(str(save_path.resolve()))
        print(f"    - [{idx}/{total_pages}] 保存完了: {save_path.name}")

    print(f"[SUCCESS] すべての画像保存が完了しました（合計 {len(saved_paths)} 枚）。")
    return saved_paths


def main():
    parser = argparse.ArgumentParser(
        description="PDFを高解像度画像に一括変換するツール"
    )
    parser.add_argument("--pdf", required=True, help="変換対象のPDFファイルパス")
    parser.add_argument(
        "--output-dir", required=True, help="画像の保存先ディレクトリパス"
    )
    parser.add_argument(
        "--dpi", type=int, default=300, help="変換解像度 (デフォルト: 300)"
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "jpg", "jpeg"],
        help="画像フォーマット (デフォルト: png)",
    )

    args = parser.parse_args()
    convert_pdf_to_images(
        pdf_path=args.pdf,
        output_dir=args.output_dir,
        dpi=args.dpi,
        fmt=args.format,
    )


if __name__ == "__main__":
    main()
