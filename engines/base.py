from abc import ABC, abstractmethod
from pathlib import Path


class OCREngine(ABC):
    """OCR 引擎抽象基类。所有 OCR 引擎必须实现此接口。"""

    @abstractmethod
    def recognize(self, image_path: Path) -> str:
        """对单张图片进行 OCR，返回 markdown 文本。

        Args:
            image_path: 图片文件路径。

        Returns:
            识别出的 markdown 文本内容。
        """
        ...

    def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
        """直接解析 PDF，返回 markdown 文本。

        默认不支持，子类可按需覆写。

        Args:
            pdf_path: PDF 文件路径。
            pages: 页码范围字符串（如 "1-3,5"），None 表示全部。

        Returns:
            解析出的 markdown 文本内容。

        Raises:
            NotImplementedError: 如果引擎不支持直接解析 PDF。
        """
        raise NotImplementedError(f"{self.__class__.__name__} 不支持直接解析 PDF")
