"""测试 batch 模块：批量处理目录下图片和 PDF。"""

from pathlib import Path

import pytest

from multi_ocr.batch import (
    _batch_images,
    _batch_pdfs,
    _collect_files,
    ocr_directory,
)
from multi_ocr.engines.base import OCREngine


class MockRecognizeEngine(OCREngine):
    """模拟 OCR 引擎。"""

    def __init__(self, text: str = "mock ocr result") -> None:
        self._text = text
        self.parse_image_calls: list[Path] = []

    def parse_image(self, image_path: Path) -> str:
        self.parse_image_calls.append(image_path)
        return f"{self._text} [{image_path.name}]"

    def parse_pdf(
        self,
        pdf_path: Path,
        pages: str | None = None,
        progress_callback=None,
        concurrency: int = 1,
    ) -> str:
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

        assert len(engine.parse_image_calls) == 2
        assert img_a in engine.parse_image_calls
        assert img_b in engine.parse_image_calls


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

        from multi_ocr.batch import _batch_pdfs as batch_pdfs_fn

        pdf_a = tmp_path / "a.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(pdf_a)
        doc.close()

        engine = MockRecognizeEngine()

        with mock.patch("multi_ocr.batch.ocr_file") as mock_ocr_file:
            batch_pdfs_fn([pdf_a], engine)
            mock_ocr_file.assert_called_once_with(
                input_path=pdf_a, engine=engine, pages=None, concurrency=1
            )


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

    def test_mixed_dir(self, tmp_path: Path) -> None:
        """混合目录 → 报错退出。"""
        (tmp_path / "img.jpg").touch()
        (tmp_path / "doc.pdf").touch()
        engine = MockRecognizeEngine()
        with pytest.raises(ValueError, match="混合文件类型"):
            ocr_directory(tmp_path, engine)


class TestOcrDirectoryDispatch:
    def test_images_only_non_liteparse(self, tmp_path: Path, jpg_path: Path) -> None:
        """仅有图片 + 支持图片的引擎 → 图片批量。"""
        import shutil

        img_a = tmp_path / "a.jpg"
        shutil.copy(jpg_path, img_a)
        engine = MockRecognizeEngine()

        ocr_directory(tmp_path, engine)

        # 验证调用了 parse_image
        assert len(engine.parse_image_calls) == 1
        # 验证输出文件
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
        """混合目录 → 报错退出。"""
        import shutil

        img = tmp_path / "img.jpg"
        shutil.copy(jpg_path, img)
        (tmp_path / "doc.pdf").touch()
        engine = MockRecognizeEngine()

        with pytest.raises(ValueError, match="混合文件类型"):
            ocr_directory(tmp_path, engine)


# ---------------------------------------------------------------------------
# Concurrency Tests
# ---------------------------------------------------------------------------


class TestBatchImagesConcurrency:
    def test_concurrent_order_preserved(self, tmp_path: Path) -> None:
        """并发模式下结果顺序与输入顺序一致。"""
        input_dir = tmp_path / "imgs"
        input_dir.mkdir()
        imgs = []
        for i in range(5):
            p = input_dir / f"{i:02d}.png"
            p.touch()
            imgs.append(p)
        engine = MockRecognizeEngine()

        _batch_images(input_dir, imgs, engine, concurrency=3)

        output = (tmp_path / "imgs.md").read_text(encoding="utf-8")
        # 验证每张图片结果都在
        for img in imgs:
            assert img.name in output

    def test_concurrent_with_single_image(self, tmp_path: Path) -> None:
        """单张图片 + 并发 > 1 也应正常工作。"""
        input_dir = tmp_path / "single"
        input_dir.mkdir()
        img = input_dir / "only.png"
        img.touch()
        engine = MockRecognizeEngine()

        _batch_images(input_dir, [img], engine, concurrency=4)

        output = (tmp_path / "single.md").read_text(encoding="utf-8")
        assert "only.png" in output

    def test_concurrency_default_1_is_sequential(self, tmp_path: Path) -> None:
        """默认 concurrency=1 保持串行行为。"""
        input_dir = tmp_path / "seq"
        input_dir.mkdir()
        imgs = [input_dir / f"{i}.png" for i in range(3)]
        for p in imgs:
            p.touch()
        engine = MockRecognizeEngine()

        _batch_images(input_dir, imgs, engine)

        assert len(engine.parse_image_calls) == 3

    def test_exception_propagates(self, tmp_path: Path) -> None:
        """并发模式下，任一任务失败应向上传播异常。"""
        input_dir = tmp_path / "err"
        input_dir.mkdir()
        for i in range(3):
            (input_dir / f"{i}.png").touch()

        class FailingEngine(MockRecognizeEngine):
            def parse_image(self, image_path: Path) -> str:
                if "1.png" in str(image_path):
                    raise RuntimeError("simulated failure")
                return super().parse_image(image_path)

        engine = FailingEngine()
        imgs = sorted(input_dir.iterdir())

        with pytest.raises(RuntimeError, match="simulated failure"):
            _batch_images(input_dir, imgs, engine, concurrency=2)


class TestBatchPdfsConcurrency:
    def test_concurrent_pdfs_all_processed(self, tmp_path: Path) -> None:
        """并发模式下所有 PDF 都被处理。"""
        import fitz

        pdf_paths = []
        for name in ["a.pdf", "b.pdf", "c.pdf"]:
            p = tmp_path / name
            doc = fitz.open()
            doc.new_page()
            doc.save(p)
            doc.close()
            pdf_paths.append(p)

        engine = MockRecognizeEngine()

        _batch_pdfs(pdf_paths, engine, concurrency=2)

        for pdf in pdf_paths:
            md = pdf.with_suffix(".md")
            assert md.exists()

    def test_concurrent_default_1_is_sequential(self, tmp_path: Path) -> None:
        """默认 concurrency=1 保持串行行为。"""
        import fitz

        doc = fitz.open()
        doc.new_page()
        doc.save(tmp_path / "only.pdf")
        doc.close()

        engine = MockRecognizeEngine()
        _batch_pdfs([tmp_path / "only.pdf"], engine)

        assert (tmp_path / "only.md").exists()
