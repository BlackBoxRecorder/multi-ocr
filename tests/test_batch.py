"""测试 batch 模块：批量处理目录下图片和 PDF。"""

from pathlib import Path

import pytest

from batch import (
    _batch_images,
    _batch_pdfs,
    _collect_files,
    _images_to_pdf_and_parse,
    ocr_directory,
)
from engines.base import OCREngine


class MockRecognizeEngine(OCREngine):
    """模拟支持 recognize 的引擎（如 SiliconFlow / DashScope）。"""

    def __init__(self, text: str = "mock ocr result") -> None:
        self._text = text
        self.recognize_calls: list[Path] = []

    def recognize(self, image_path: Path) -> str:
        self.recognize_calls.append(image_path)
        return f"{self._text} [{image_path.name}]"


class MockParsePdfEngine(OCREngine):
    """模拟 LiteParse 引擎（支持 parse_pdf，不支持图片）。"""

    def __init__(self, text: str = "parsed pdf content") -> None:
        self._text = text
        self.parse_calls: list[Path] = []

    def recognize(self, image_path: Path) -> str:
        raise NotImplementedError("不支持图片识别")

    def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
        self.parse_calls.append(pdf_path)
        return self._text


# ---------------------------------------------------------------------------
# _collect_files
# ---------------------------------------------------------------------------


class TestCollectFiles:
    def test_empty_directory(self, tmp_path: Path) -> None:
        images, pdfs = _collect_files(tmp_path)
        assert images == []
        assert pdfs == []

    def test_images_only(self, tmp_path: Path) -> None:
        (tmp_path / "b.png").touch()
        (tmp_path / "a.jpg").touch()
        images, pdfs = _collect_files(tmp_path)
        assert len(images) == 2
        assert images[0].name == "a.jpg"
        assert images[1].name == "b.png"
        assert pdfs == []

    def test_pdfs_only(self, tmp_path: Path) -> None:
        (tmp_path / "b.pdf").touch()
        (tmp_path / "a.pdf").touch()
        images, pdfs = _collect_files(tmp_path)
        assert images == []
        assert len(pdfs) == 2
        assert pdfs[0].name == "a.pdf"
        assert pdfs[1].name == "b.pdf"

    def test_mixed(self, tmp_path: Path) -> None:
        (tmp_path / "img.png").touch()
        (tmp_path / "doc.pdf").touch()
        images, pdfs = _collect_files(tmp_path)
        assert len(images) == 1
        assert len(pdfs) == 1

    def test_unsupported_extensions_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "data.txt").touch()
        (tmp_path / "script.py").touch()
        images, pdfs = _collect_files(tmp_path)
        assert images == []
        assert pdfs == []

    def test_subdirectories_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        (tmp_path / "img.jpg").touch()
        images, pdfs = _collect_files(tmp_path)
        assert len(images) == 1

    def test_case_insensitive(self, tmp_path: Path) -> None:
        (tmp_path / "IMG.JPG").touch()
        (tmp_path / "DOC.PDF").touch()
        images, pdfs = _collect_files(tmp_path)
        assert len(images) == 1
        assert len(pdfs) == 1


# ---------------------------------------------------------------------------
# _batch_images
# ---------------------------------------------------------------------------


class TestBatchImages:
    def test_output_file_name(self, tmp_path: Path) -> None:
        """输出文件名为 input_dir.md，放在目录同级。"""
        input_dir = tmp_path / "photos"
        input_dir.mkdir()
        (input_dir / "1.jpg").touch()
        engine = MockRecognizeEngine()

        _batch_images(input_dir, [input_dir / "1.jpg"], engine)

        expected = tmp_path / "photos.md"
        assert expected.exists()

    def test_merged_content(self, tmp_path: Path) -> None:
        """多张图片结果用 \\n\\n 合并。"""
        input_dir = tmp_path / "scans"
        input_dir.mkdir()
        img_a = input_dir / "a.png"
        img_b = input_dir / "b.png"
        img_a.touch()
        img_b.touch()
        engine = MockRecognizeEngine()

        _batch_images(input_dir, [img_a, img_b], engine)

        output = (tmp_path / "scans.md").read_text(encoding="utf-8")
        assert "a.png" in output
        assert "b.png" in output
        # 两张结果之间用空行分隔
        assert "\n\n" in output

    def test_calls_recognize_for_each_image(self, tmp_path: Path) -> None:
        """每张图片调用一次 recognize。"""
        input_dir = tmp_path / "imgdir"
        input_dir.mkdir()
        img_a = input_dir / "a.png"
        img_b = input_dir / "b.png"
        img_a.touch()
        img_b.touch()
        engine = MockRecognizeEngine()

        _batch_images(input_dir, [img_a, img_b], engine)

        assert len(engine.recognize_calls) == 2
        assert img_a in engine.recognize_calls
        assert img_b in engine.recognize_calls


# ---------------------------------------------------------------------------
# _batch_pdfs
# ---------------------------------------------------------------------------


class TestBatchPdfs:
    def test_each_pdf_produces_md(self, tmp_path: Path) -> None:
        """每个 PDF 生成对应的 .md 文件。"""
        pdf_a = tmp_path / "a.pdf"
        pdf_b = tmp_path / "b.pdf"
        # 创建最小的有效 PDF（pymupdf/fitz 需要）
        import fitz

        for pdf_path in [pdf_a, pdf_b]:
            doc = fitz.open()
            doc.new_page()
            doc.save(pdf_path)
            doc.close()

        engine = MockRecognizeEngine()

        _batch_pdfs([pdf_a, pdf_b], engine)

        md_a = tmp_path / "a.md"
        md_b = tmp_path / "b.md"
        assert md_a.exists()
        assert md_b.exists()

    def test_calls_ocr_file_for_each_pdf(self, tmp_path: Path) -> None:
        """验证每个 PDF 都调用了 ocr_file。"""
        import fitz
        from unittest import mock

        from batch import _batch_pdfs as batch_pdfs_fn

        pdf_a = tmp_path / "a.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(pdf_a)
        doc.close()

        engine = MockRecognizeEngine()

        with mock.patch("batch.ocr_file") as mock_ocr_file:
            batch_pdfs_fn([pdf_a], engine)
            mock_ocr_file.assert_called_once_with(
                input_path=pdf_a, engine=engine, pages=None
            )


# ---------------------------------------------------------------------------
# _images_to_pdf_and_parse
# ---------------------------------------------------------------------------


class TestImagesToPdfAndParse:
    def test_calls_parse_pdf(self, tmp_path: Path, jpg_path: Path) -> None:
        """验证调用了 engine.parse_pdf 并输出到 input_dir.md。"""
        input_dir = tmp_path / "scans"
        input_dir.mkdir()
        # 复制真实图片到目录中
        import shutil

        img_a = input_dir / "a.jpg"
        img_b = input_dir / "b.jpg"
        shutil.copy(jpg_path, img_a)
        shutil.copy(jpg_path, img_b)
        engine = MockParsePdfEngine("liteparse result")

        _images_to_pdf_and_parse(input_dir, [img_a, img_b], engine)

        # 验证调用了 parse_pdf
        assert len(engine.parse_calls) == 1

        # 验证输出文件
        expected = tmp_path / "scans.md"
        assert expected.exists()
        assert expected.read_text(encoding="utf-8") == "liteparse result"

    def test_cleans_up_temp_pdf(self, tmp_path: Path, jpg_path: Path) -> None:
        """临时 PDF 在处理后被清理。"""
        input_dir = tmp_path / "scans"
        input_dir.mkdir()
        import shutil

        img_a = input_dir / "a.jpg"
        shutil.copy(jpg_path, img_a)
        engine = MockParsePdfEngine()

        _images_to_pdf_and_parse(input_dir, [img_a], engine)

        # 验证 parse_pdf 被调用时传入的路径不再存在
        called_path = engine.parse_calls[0]
        assert not called_path.exists()


# ---------------------------------------------------------------------------
# ocr_directory dispatch
# ---------------------------------------------------------------------------


class TestOcrDirectoryErrors:
    def test_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            ocr_directory(Path("/nonexistent/dir"), MockRecognizeEngine())

    def test_not_a_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.touch()
        with pytest.raises(NotADirectoryError):
            ocr_directory(f, MockRecognizeEngine())

    def test_no_supported_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").touch()
        with pytest.raises(ValueError, match="没有可处理的"):
            ocr_directory(tmp_path, MockRecognizeEngine())

    def test_mixed_dir_with_liteparse(self, tmp_path: Path) -> None:
        (tmp_path / "img.jpg").touch()
        (tmp_path / "doc.pdf").touch()
        with pytest.raises(ValueError, match="混合目录"):
            ocr_directory(tmp_path, MockParsePdfEngine())


class TestOcrDirectoryDispatch:
    def test_images_only_non_liteparse(self, tmp_path: Path, jpg_path: Path) -> None:
        """仅有图片 + 支持图片的引擎 → 图片批量。"""
        import shutil

        img_a = tmp_path / "a.jpg"
        shutil.copy(jpg_path, img_a)
        engine = MockRecognizeEngine()

        ocr_directory(tmp_path, engine)

        # 验证调用了 recognize
        assert len(engine.recognize_calls) == 1
        # 验证输出文件
        assert tmp_path.with_suffix(".md").exists()

    def test_images_only_liteparse(self, tmp_path: Path, jpg_path: Path) -> None:
        """仅有图片 + liteparse → 图片合并为 PDF 再解析。"""
        import shutil

        img_a = tmp_path / "a.jpg"
        shutil.copy(jpg_path, img_a)
        engine = MockParsePdfEngine()

        ocr_directory(tmp_path, engine)

        assert len(engine.parse_calls) == 1
        assert tmp_path.with_suffix(".md").exists()

    def test_pdfs_only(self, tmp_path: Path) -> None:
        """仅有 PDF → PDF 批量。"""
        import fitz

        doc = fitz.open()
        doc.new_page()
        doc.save(tmp_path / "doc.pdf")
        doc.close()

        engine = MockRecognizeEngine()

        ocr_directory(tmp_path, engine)

        assert (tmp_path / "doc.md").exists()

    def test_mixed_non_liteparse(self, tmp_path: Path, jpg_path: Path) -> None:
        """混合目录 + 非 liteparse → 图片批量。"""
        import shutil

        img = tmp_path / "img.jpg"
        shutil.copy(jpg_path, img)
        (tmp_path / "doc.pdf").touch()
        engine = MockRecognizeEngine()

        ocr_directory(tmp_path, engine)

        # 应该走了图片批量流程
        assert len(engine.recognize_calls) == 1
        assert tmp_path.with_suffix(".md").exists()
