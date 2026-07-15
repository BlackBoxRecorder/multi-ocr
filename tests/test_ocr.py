"""测试 ocr 模块：OCR 识别入口函数。"""

from pathlib import Path

import pytest

from ocr import _is_image, _is_pdf, ocr_file


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
        """默认保存 .txt 文件。"""
        expected_txt = jpg_path.with_suffix(".txt")
        expected_txt.unlink(missing_ok=True)

        try:
            result = ocr_file(input_path=jpg_path, engine=mock_engine)
            assert expected_txt.exists()
            assert expected_txt.read_text(encoding="utf-8") == result
        finally:
            expected_txt.unlink(missing_ok=True)

    def test_image_ocr_with_custom_engine(self, jpg_path: Path, custom_engine) -> None:
        """使用自定义引擎的识别。"""
        result = ocr_file(input_path=jpg_path, engine=custom_engine)
        assert "custom text" in result
        assert "1.jpg" in result
