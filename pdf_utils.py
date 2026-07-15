import tempfile
from pathlib import Path

import fitz  # pymupdf


def parse_pages(pages_str: str, total_pages: int) -> list[int]:
    """解析页码范围字符串，返回 0-based 页码列表。

    格式：逗号分隔的页码和范围，如 "1,3-5,8"。

    Args:
        pages_str: 页码范围字符串。
        total_pages: PDF 总页数。

    Returns:
        0-based 页码列表（已去重并排序）。

    Raises:
        ValueError: 如果范围格式无效或页码越界。
    """
    result: set[int] = set()
    parts = [p.strip() for p in pages_str.split(",") if p.strip()]

    for part in parts:
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start, end = int(start_str.strip()), int(end_str.strip())
            except ValueError:
                raise ValueError(f"无效的页码范围: {part}")
            if start < 1 or end > total_pages or start > end:
                raise ValueError(f"页码范围越界: {part}（总页数: {total_pages}）")
            for i in range(start, end + 1):
                result.add(i - 1)
        else:
            try:
                page = int(part)
            except ValueError:
                raise ValueError(f"无效的页码: {part}")
            if page < 1 or page > total_pages:
                raise ValueError(f"页码越界: {page}（总页数: {total_pages}）")
            result.add(page - 1)

    return sorted(result)


def pdf_to_images(pdf_path: Path, pages: list[int] | None = None) -> list[Path]:
    """将 PDF 渲染为 PNG 图片列表。

    Args:
        pdf_path: PDF 文件路径。
        pages: 要渲染的 0-based 页码列表，None 表示全部页。

    Returns:
        临时 PNG 图片路径列表。
    """
    doc = fitz.open(pdf_path)
    total = doc.page_count

    if total == 0:
        doc.close()
        return []

    if pages is None:
        pages = list(range(total))

    tmp_dir = Path(tempfile.mkdtemp(prefix="multiocr_"))
    image_paths: list[Path] = []

    for page_num in pages:
        if page_num < 0 or page_num >= total:
            continue
        page = doc[page_num]
        pix = page.get_pixmap(dpi=200)
        img_path = tmp_dir / f"page_{page_num + 1:04d}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)

    doc.close()
    return image_paths


def images_to_pdf(image_paths: list[Path], output_path: Path) -> Path:
    """将多张图片按顺序合并为一个 PDF 文件。

    每张图片作为独立的一页，原图嵌入。

    Args:
        image_paths: 图片文件路径列表，按页面顺序排列。
        output_path: 输出的 PDF 文件路径。

    Returns:
        输出的 PDF 文件路径。
    """
    pdf_doc = fitz.open()
    try:
        for img_path in image_paths:
            img_doc = fitz.open(img_path)
            page = img_doc[0]
            pix = page.get_pixmap()
            img_doc.close()

            # 创建新页面，大小与图片一致
            pdf_page = pdf_doc.new_page(width=pix.width, height=pix.height)
            pdf_page.insert_image(
                pdf_page.rect,
                pixmap=pix,
            )
        pdf_doc.save(output_path)
        return output_path
    finally:
        pdf_doc.close()
