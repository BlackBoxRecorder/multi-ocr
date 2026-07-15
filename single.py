import sys
from pathlib import Path

import fitz
from tqdm import tqdm

from engines.base import OCREngine
from pdf_utils import parse_pages

# 支持的图片格式
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _is_image(file_path: Path) -> bool:
    return file_path.suffix.lower() in _IMAGE_EXTENSIONS


def _is_pdf(file_path: Path) -> bool:
    return file_path.suffix.lower() == ".pdf"


def ocr_file(
    input_path: Path,
    engine: OCREngine,
    pages: str | None = None,
) -> str:
    """对 PDF 或图片文件执行 OCR。

    Args:
        input_path: 输入文件路径（PDF 或图片）。
        engine: OCR 引擎实例。
        pages: 页码范围字符串（仅对 PDF 有效），如 "1-3,5"。

    Returns:
        合并后的 OCR 文本。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的文件格式或页码范围无效。
    """
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_path}")

    if _is_pdf(input_path):
        # 获取实际要处理的页数
        doc = fitz.open(input_path)
        total_pages = doc.page_count
        doc.close()

        if pages:
            page_indices = parse_pages(pages, total_pages)
            actual_total = len(page_indices)
        else:
            actual_total = total_pages

        if actual_total == 0:
            merged = ""
        else:
            pbar = tqdm(
                total=actual_total,
                desc=f"识别 {input_path.name}",
                file=sys.stderr,
                unit="页",
            )
            try:
                merged = engine.parse_pdf(
                    input_path,
                    pages,
                    progress_callback=lambda: pbar.update(1),
                )
                # 确保进度条到达 100%（兼容 LiteParse 等无逐页回调的引擎）
                pbar.update(pbar.total - pbar.n)
            finally:
                pbar.close()
    elif _is_image(input_path):
        if pages:
            raise ValueError("图片不支持 --pages 页码范围，该参数仅对 PDF 有效")
        merged = engine.parse_image(input_path)
    else:
        supported = ", ".join(_IMAGE_EXTENSIONS | {".pdf"})
        raise ValueError(f"不支持的文件格式: {input_path.suffix}，支持: {supported}")

    # 输出
    output_path = input_path.with_suffix(".md")
    output_path.write_text(merged, encoding="utf-8")
    print(f"已保存: {output_path}")

    return merged
