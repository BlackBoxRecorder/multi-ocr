from pathlib import Path

from engines.base import OCREngine

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
        merged = engine.parse_pdf(input_path, pages)
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
