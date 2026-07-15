from pathlib import Path
import tempfile
from typing import Callable

from liteparse import LiteParse as LiteParseLib

from engines.base import OCREngine
from pdf_utils import images_to_pdf


class LiteParseEngine(OCREngine):
    """LiteParse 本地 PDF 解析引擎。

    基于 Rust 实现，无需 API Key、无需联网，直接解析 PDF 并输出 markdown。
    图片通过自动转换为 PDF 后解析来支持。
    """

    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        base_url: str | None = None,
    ) -> None:
        # model / api_key / base_url 不使用，保留参数以兼容工厂函数签名
        self._model = model
        self._api_key = api_key

    def parse_image(self, image_path: Path) -> str:
        """将图片转为 PDF 后解析，返回 markdown 文本。"""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_pdf = Path(f.name)
        try:
            images_to_pdf([image_path], tmp_pdf)
            return self.parse_pdf(tmp_pdf)
        finally:
            tmp_pdf.unlink(missing_ok=True)

    def parse_pdf(
        self,
        pdf_path: Path,
        pages: str | None = None,
        progress_callback: Callable[[], None] | None = None,
    ) -> str:
        """直接解析 PDF，返回 markdown 文本。

        Args:
            pdf_path: PDF 文件路径。
            pages: 页码范围字符串（如 "1-3,5"），None 表示全部。

        Returns:
            解析出的 markdown 文本内容。
        """
        kwargs: dict = {}
        if pages:
            kwargs["target_pages"] = pages
        parser = LiteParseLib(output_format="markdown", **kwargs)
        result = parser.parse(str(pdf_path))
        return result.text
