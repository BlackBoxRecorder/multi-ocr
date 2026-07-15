from abc import ABC, abstractmethod
from pathlib import Path


class OCREngine(ABC):
    """OCR 引擎抽象基类。所有 OCR 引擎必须实现此接口。"""

    @abstractmethod
    def recognize(self, image_path: Path) -> str:
        """对单张图片进行 OCR，返回识别文本。

        Args:
            image_path: 图片文件路径。

        Returns:
            识别出的文本内容。
        """
        ...
