"""批量处理模块：对目录下的图片或 PDF 进行批量 OCR。"""

import sys
import tempfile
from pathlib import Path

from tqdm import tqdm

from engines.base import OCREngine
from ocr import ocr_file
from pdf_utils import images_to_pdf

# 支持的图片格式
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _collect_files(input_dir: Path) -> tuple[list[Path], list[Path]]:
    """扫描目录，收集图片和 PDF 文件，均按文件名排序。

    Args:
        input_dir: 输入目录路径。

    Returns:
        (图片文件路径列表, PDF 文件路径列表)，均已按文件名排序。
    """
    images: list[Path] = []
    pdfs: list[Path] = []

    for entry in sorted(input_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_file():
            continue
        if entry.suffix.lower() in _IMAGE_EXTENSIONS:
            images.append(entry)
        elif entry.suffix.lower() == ".pdf":
            pdfs.append(entry)

    return images, pdfs


def _batch_images(input_dir: Path, images: list[Path], engine: OCREngine) -> None:
    """图片批量处理：逐张识别，合并结果写入 input_dir.md。

    Args:
        input_dir: 输入目录路径。
        images: 已排序的图片文件路径列表。
        engine: OCR 引擎实例。
    """
    results: list[str] = []

    for img_path in tqdm(images, desc=f"处理 {input_dir.name} 目录", file=sys.stderr):
        text = engine.recognize(img_path)
        results.append(text)

    merged = "\n\n".join(results)
    output_path = input_dir.with_suffix(".md")
    output_path.write_text(merged, encoding="utf-8")
    print(f"已保存: {output_path}")


def _batch_pdfs(pdfs: list[Path], engine: OCREngine) -> None:
    """PDF 批量处理：逐文件调用 ocr_file()，各自输出 .md 文件。

    Args:
        pdfs: 已排序的 PDF 文件路径列表。
        engine: OCR 引擎实例。
    """
    for pdf_path in tqdm(pdfs, desc="处理 PDF", file=sys.stderr):
        ocr_file(input_path=pdf_path, engine=engine, pages=None)


def _images_to_pdf_and_parse(
    input_dir: Path, images: list[Path], engine: OCREngine
) -> None:
    """图片目录合并为 PDF，再用 LiteParse 解析。

    适用于 liteparse 引擎（不支持图片直接识别）处理图片目录的场景。

    Args:
        input_dir: 输入目录路径。
        images: 已排序的图片文件路径列表。
        engine: LiteParse 引擎实例。
    """
    print(f"正在将 {len(images)} 张图片合并为 PDF...", file=sys.stderr)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_pdf_path = Path(tmp_file.name)

    try:
        images_to_pdf(images, tmp_pdf_path)
        print("PDF 合并完成，开始解析...", file=sys.stderr)
        merged = engine.parse_pdf(tmp_pdf_path)
        output_path = input_dir.with_suffix(".md")
        output_path.write_text(merged, encoding="utf-8")
        print(f"已保存: {output_path}")
    finally:
        tmp_pdf_path.unlink(missing_ok=True)


def ocr_directory(input_dir: Path, engine: OCREngine) -> None:
    """批量处理目录下的图片或 PDF 文件。

    根据目录内容与引擎类型自动选择处理分支：
    - 仅有图片 + 非 liteparse → 图片批量流程（合并输出）
    - 仅有图片 + liteparse → 图片合并为 PDF 再解析
    - 仅有 PDF → PDF 批量流程（各自输出）
    - 混合目录 + 非 liteparse → 图片批量流程
    - 混合目录 + liteparse → 报错

    Args:
        input_dir: 输入目录路径。
        engine: OCR 引擎实例。

    Raises:
        FileNotFoundError: 目录不存在。
        ValueError: 目录中没有可处理的文件，或 liteparse 遇到混合目录。
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"目录不存在: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"不是目录: {input_dir}")

    images, pdfs = _collect_files(input_dir)

    if not images and not pdfs:
        raise ValueError(f"目录中没有可处理的图片或 PDF 文件: {input_dir}")

    # 分发处理
    # 混合目录 + 引擎不支持图片 → 报错
    if images and pdfs:
        raise ValueError(
            "当前引擎不支持图片识别，且混合目录无法统一处理（同时包含图片和 PDF）。"
        )

    has_parse_pdf = type(engine).parse_pdf is not OCREngine.parse_pdf

    if images and pdfs:
        # 混合目录 + 支持图片的引擎 → 按图片批量处理
        _batch_images(input_dir, images, engine)
    elif images and has_parse_pdf:
        # 仅有图片 + 支持 parse_pdf → 合并为 PDF 再解析
        _images_to_pdf_and_parse(input_dir, images, engine)
    elif images:
        # 仅有图片 + 支持图片的引擎 → 图片批量
        _batch_images(input_dir, images, engine)
    else:
        # 仅有 PDF
        _batch_pdfs(pdfs, engine)
