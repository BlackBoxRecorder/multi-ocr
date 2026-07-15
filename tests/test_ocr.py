"""测试 ocr 模块：OCR 识别入口函数。"""

from pathlib import Path

import pytest

from engines.base import OCREngine
from ocr import _is_image, _is_pdf, ocr_file


class MockParsePdfEngine(OCREngine):
    """模拟支持 parse_pdf 的引擎（如 LiteParse）。"""

    def __init__(self) -> None:
        pass

    def recognize(self, image_path: Path) -> str:
        raise NotImplementedError("仅支持 PDF")

    def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
        result = f"parsed: {pdf_path.name}"
        if pages:
            result += f" pages={pages}"
        return result


class TestFileTypeHelpers:
    """测试 _is_image / _is_pdf 文件类型判断。"""

    def test_is_image_jpg(self) -> None:
        assert _is_image(Path("test.jpg")) is True

    def test_is_image_jpeg(self) -> None:
        assert _is_image(Path("test.jpeg")) is True

    def test_is_image_png(self) -> None:
        assert _is_image(Path("test.png")) is True

    def test_is_image_pdf(self) -> None:
        assert _is_image(Path("test.pdf")) is False

    def test_is_image_uppercase(self) -> None:
        assert _is_image(Path("test.JPG")) is True

    def test_is_image_no_extension(self) -> None:
        assert _is_image(Path("test")) is False

    def test_is_pdf_pdf(self) -> None:
        assert _is_pdf(Path("test.pdf")) is True

    def test_is_pdf_jpg(self) -> None:
        assert _is_pdf(Path("test.jpg")) is False

    def test_is_pdf_uppercase(self) -> None:
        assert _is_pdf(Path("test.PDF")) is True


class TestOcrFile:
    """测试 ocr_file 主流程。"""

    def test_image_ocr(self, jpg_path: Path, mock_engine, tmp_path: Path) -> None:
        """图片 OCR：返回引擎识别文本。"""
        result = ocr_file(input_path=jpg_path, engine=mock_engine)
        assert "mock ocr result" in result
        assert "1.jpg" in result

    def test_pdf_ocr(self, pdf_path: Path, mock_engine) -> None:
        """PDF OCR：每页标注页码。"""
        result = ocr_file(input_path=pdf_path, engine=mock_engine)
        assert "mock ocr result" in result
        assert "--- 第" in result
        assert "页 ---" in result

    def test_pdf_with_page_range(self, pdf_path: Path, mock_engine) -> None:
        """PDF OCR 指定页码范围。"""
        result = ocr_file(input_path=pdf_path, engine=mock_engine, pages="1")
        assert "--- 第 1 页 ---" in result

    def test_file_not_found(self, mock_engine) -> None:
        """不存在的文件抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            ocr_file(input_path=Path("/nonexistent/file.png"), engine=mock_engine)

    def test_unsupported_format(self, mock_engine, tmp_path: Path) -> None:
        """不支持的文件格式抛出 ValueError。"""
        bmp_file = tmp_path / "test.bmp"
        bmp_file.write_text("fake bmp content")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            ocr_file(input_path=bmp_file, engine=mock_engine)

    def test_save_to_file(self, jpg_path: Path, mock_engine) -> None:
        """默认保存 .md 文件。"""
        expected_md = jpg_path.with_suffix(".md")
        expected_md.unlink(missing_ok=True)

        try:
            result = ocr_file(input_path=jpg_path, engine=mock_engine)
            assert expected_md.exists()
            assert expected_md.read_text(encoding="utf-8") == result
        finally:
            expected_md.unlink(missing_ok=True)

    def test_image_ocr_with_custom_engine(self, jpg_path: Path, custom_engine) -> None:
        """使用自定义引擎的识别。"""
        result = ocr_file(input_path=jpg_path, engine=custom_engine)
        assert "custom text" in result
        assert "1.jpg" in result

    def test_pdf_with_parse_pdf_engine(self, pdf_path: Path) -> None:
        """PDF + 支持 parse_pdf 的引擎 → 跳过拆页，直接解析。"""
        engine = MockParsePdfEngine()
        result = ocr_file(input_path=pdf_path, engine=engine)
        assert "parsed: 2.pdf" in result

    def test_pdf_with_parse_pdf_engine_and_pages(self, pdf_path: Path) -> None:
        """PDF + parse_pdf 引擎 + 页码范围 → 透传 pages。"""
        engine = MockParsePdfEngine()
        result = ocr_file(input_path=pdf_path, engine=engine, pages="1-2")
        assert "parsed: 2.pdf pages=1-2" in result
