import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from pdf_utils import split_pdf


class OCREngine(ABC):
    """OCR 引擎抽象基类。所有 OCR 引擎必须实现此接口。"""

    @abstractmethod
    def parse_image(self, image_path: Path) -> str:
        """对单张图片进行 OCR，返回 markdown 文本。

        Args:
            image_path: 图片文件路径。

        Returns:
            识别出的 markdown 文本内容。
        """
        ...

    def parse_pdf(
        self,
        pdf_path: Path,
        pages: str | None = None,
        progress_callback: Callable[[], None] | None = None,
    ) -> str:
        """解析 PDF，返回 markdown 文本。

        默认实现：拆页 → 逐页调用 parse_image() → 合并结果。
        子类可覆盖以提供原生 PDF 解析（如 LiteParse）。

        Args:
            pdf_path: PDF 文件路径。
            pages: 页码范围字符串（如 "1-3,5"），None 表示全部。
            progress_callback: 每处理完一页时调用（可选）。

        Returns:
            解析出的 markdown 文本内容。
        """
        image_paths, page_labels = split_pdf(pdf_path, pages)
        try:
            results = []
            for img_path, label in zip(image_paths, page_labels):
                text = self.parse_image(img_path)
                results.append(f"--- 第 {label} 页 ---\n{text}")
                if progress_callback:
                    progress_callback()
            return "\n\n".join(results)
        finally:
            if image_paths:
                shutil.rmtree(image_paths[0].parent, ignore_errors=True)
