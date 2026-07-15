"""批量处理模块：对目录下的图片或 PDF 进行批量 OCR。

目录下只能有一种类型的文件（全图片或全 PDF），混合目录直接报错。
"""

import sys
from pathlib import Path

from tqdm import tqdm

from engines.base import OCREngine
from single import ocr_file

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
        text = engine.parse_image(img_path)
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
    for pdf_path in pdfs:
        ocr_file(input_path=pdf_path, engine=engine, pages=None)


def ocr_directory(input_dir: Path, engine: OCREngine) -> None:
    """批量处理目录下的图片或 PDF 文件。

    目录下只能有一种类型的文件（全图片或全 PDF），混合目录直接报错。

    根据目录内容与引擎类型自动选择处理分支：
    - 仅有图片 + 原生 PDF 引擎 → 图片合并为 PDF 再解析（更高效）
    - 仅有图片 + 其他引擎 → 图片批量流程（合并输出）
    - 仅有 PDF → PDF 批量流程（各自输出）

    Args:
        input_dir: 输入目录路径。
        engine: OCR 引擎实例。

    Raises:
        FileNotFoundError: 目录不存在。
        ValueError: 目录中没有可处理的文件，或包含混合文件类型。
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"目录不存在: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"不是目录: {input_dir}")

    images, pdfs = _collect_files(input_dir)

    # 严格检查：不允许混合文件类型
    if images and pdfs:
        raise ValueError(
            f"目录中包含混合文件类型（图片和 PDF），请确保目录下只有一种类型的文件。\n"
            f"  图片: {len(images)} 个 (.png/.jpg/.jpeg)\n"
            f"  PDF:  {len(pdfs)} 个 (.pdf)"
        )

    if not images and not pdfs:
        raise ValueError(f"目录中没有可处理的图片或 PDF 文件: {input_dir}")

    if images:
        _batch_images(input_dir, images, engine)
    else:
        _batch_pdfs(pdfs, engine)
