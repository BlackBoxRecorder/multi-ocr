import shutil
import sys
from pathlib import Path

from engines.base import OCREngine
from pdf_utils import parse_pages, pdf_to_images

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
    stdout: bool = False,
) -> str:
    """对 PDF 或图片文件执行 OCR。

    Args:
        input_path: 输入文件路径（PDF 或图片）。
        engine: OCR 引擎实例。
        pages: 页码范围字符串（仅对 PDF 有效），如 "1-3,5"。
        stdout: True 则打印到终端，False 则保存文件。

    Returns:
        合并后的 OCR 文本。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的文件格式或页码范围无效。
    """
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_path}")

    if _is_pdf(input_path):
        images, page_labels = _prepare_pdf(input_path, pages)
    elif _is_image(input_path):
        images, page_labels = [input_path], [None]
    else:
        supported = ", ".join(_IMAGE_EXTENSIONS | {".pdf"})
        raise ValueError(f"不支持的文件格式: {input_path.suffix}，支持: {supported}")

    if not images:
        print("没有需要处理的页面。", file=sys.stderr)
        sys.exit(1)

    # 逐页识别
    results: list[str] = []
    for i, img_path in enumerate(images):
        try:
            text = engine.recognize(img_path)
        except Exception as e:
            print(f"OCR 识别失败 (第 {i + 1} 个图片): {e}", file=sys.stderr)
            raise
        label = page_labels[i]
        if label is not None:
            results.append(f"--- 第 {label} 页 ---\n{text}")
        else:
            results.append(text)

    merged = "\n\n".join(results)

    # 输出
    if stdout:
        print(merged)
    else:
        output_path = input_path.with_suffix(".txt")
        output_path.write_text(merged, encoding="utf-8")
        print(f"已保存: {output_path}")

    return merged


def _prepare_pdf(
    pdf_path: Path, pages_str: str | None
) -> tuple[list[Path], list[int | None]]:
    """准备 PDF：拆页并过滤页码范围。

    Returns:
        (图片路径列表, 页码标签列表)，标签为 1-based 页码。
    """
    import fitz

    doc = fitz.open(pdf_path)
    total = doc.page_count
    doc.close()

    if total == 0:
        print("PDF 无内容。", file=sys.stderr)
        sys.exit(1)

    if pages_str:
        page_indices = parse_pages(pages_str, total)
    else:
        page_indices = list(range(total))

    images = pdf_to_images(pdf_path, page_indices)

    # 生成页码标签（1-based）
    labels = [i + 1 for i in page_indices]

    return images, labels


def cleanup_images(images: list[Path]) -> None:
    """清理临时图片目录。"""
    if images:
        tmp_dir = images[0].parent
        shutil.rmtree(tmp_dir, ignore_errors=True)
