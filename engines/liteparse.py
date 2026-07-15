from pathlib import Path

from liteparse import LiteParse as LiteParseLib

from engines.base import OCREngine


class LiteParseEngine(OCREngine):
    """LiteParse 本地 PDF 解析引擎。

    基于 Rust 实现，无需 API Key、无需联网，直接解析 PDF 并输出 markdown。
    仅支持 PDF，不支持图片文件。
    """

    def __init__(self, model: str = "", api_key: str = "") -> None:
        # model 和 api_key 不使用，保留参数以兼容工厂函数签名
        self._model = model
        self._api_key = api_key

    def recognize(self, image_path: Path) -> str:
        raise NotImplementedError("LiteParse 不支持图片识别，仅支持 PDF")

    def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
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
