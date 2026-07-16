"""测试 pdf_utils 模块：页码范围解析与 PDF 转图片。"""

from pathlib import Path

import pytest

from multi_ocr.pdf_utils import images_to_pdf, parse_pages, pdf_to_images, split_pdf


class TestParsePages:
    """测试 parse_pages：将用户输入的页码范围字符串转为 0-based 列表。"""

    # ── 正常场景 ──────────────────────────────────────────────

    def test_single_page(self) -> None:
        assert parse_pages("1", 5) == [0]

    def test_multiple_pages(self) -> None:
        assert parse_pages("1,3,5", 5) == [0, 2, 4]

    def test_range(self) -> None:
        assert parse_pages("1-3", 5) == [0, 1, 2]

    def test_mixed(self) -> None:
        assert parse_pages("1,3-5,8", 10) == [0, 2, 3, 4, 7]

    def test_out_of_order(self) -> None:
        assert parse_pages("5,1,3", 5) == [0, 2, 4]

    def test_with_spaces(self) -> None:
        assert parse_pages(" 1 , 3-5 ", 10) == [0, 2, 3, 4]

    def test_single_range_page(self) -> None:
        assert parse_pages("3-3", 5) == [2]

    def test_last_page(self) -> None:
        assert parse_pages("5", 5) == [4]

    def test_full_range(self) -> None:
        assert parse_pages("1-10", 10) == list(range(10))

    # ── 边界场景 ──────────────────────────────────────────────

    def test_page_1_based(self) -> None:
        """确认页码是 1-based。"""
        assert parse_pages("1", 1) == [0]
        assert parse_pages("2", 2) == [1]

    # ── 异常场景 ──────────────────────────────────────────────

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="无效的(页码|页码范围)"):
            parse_pages("abc", 10)

    def test_page_out_of_bounds_high(self) -> None:
        with pytest.raises(ValueError, match="越界"):
            parse_pages("11", 10)

    def test_page_out_of_bounds_low(self) -> None:
        with pytest.raises(ValueError, match="越界"):
            parse_pages("0", 10)

    def test_range_out_of_bounds_high(self) -> None:
        with pytest.raises(ValueError, match="越界"):
            parse_pages("8-12", 10)

    def test_range_out_of_bounds_low(self) -> None:
        with pytest.raises(ValueError, match="越界"):
            parse_pages("0-3", 10)

    def test_range_start_gt_end(self) -> None:
        with pytest.raises(ValueError, match="越界"):
            parse_pages("5-3", 10)

    def test_invalid_range_format(self) -> None:
        with pytest.raises(ValueError, match="无效的页码范围"):
            parse_pages("a-b", 10)

    def test_invalid_page_in_range(self) -> None:
        with pytest.raises(ValueError, match="无效的页码范围"):
            parse_pages("1-x", 10)

    def test_empty_string(self) -> None:
        """空字符串返回空列表。"""
        assert parse_pages("", 5) == []

    def test_only_commas(self) -> None:
        """只有逗号时返回空列表。"""
        assert parse_pages(",,,", 5) == []


class TestPdfToImages:
    """测试 pdf_to_images：将 PDF 页渲染为临时 PNG 图片。"""

    def test_all_pages(self, pdf_path: Path) -> None:
        images = pdf_to_images(pdf_path)
        assert len(images) > 0
        for img in images:
            assert img.suffix == ".png"
            assert img.exists()

    def test_specific_pages(self, pdf_path: Path) -> None:
        images = pdf_to_images(pdf_path, pages=[0])
        assert len(images) == 1
        assert images[0].suffix == ".png"
        assert images[0].exists()

    def test_out_of_range_page_skipped(self, pdf_path: Path) -> None:
        images = pdf_to_images(pdf_path, pages=[999])
        assert images == []

    def test_output_in_temp_dir(self, pdf_path: Path) -> None:
        images = pdf_to_images(pdf_path, pages=[0])
        assert len(images) == 1
        assert "multiocr_" in str(images[0].parent)

    def test_consecutive_calls_different_dirs(self, pdf_path: Path) -> None:
        imgs1 = pdf_to_images(pdf_path, pages=[0])
        imgs2 = pdf_to_images(pdf_path, pages=[0])
        assert imgs1[0].parent != imgs2[0].parent


class TestImagesToPdf:
    """测试 images_to_pdf：将多张图片合并为一个 PDF。"""

    def test_creates_pdf(self, jpg_path: Path, tmp_path: Path) -> None:
        output = tmp_path / "merged.pdf"
        result = images_to_pdf([jpg_path], output)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_multi_page_pdf(self, jpg_path: Path, tmp_path: Path) -> None:
        """多张图片合并后 PDF 应有对应页数。"""
        import fitz

        output = tmp_path / "merged.pdf"
        images_to_pdf([jpg_path, jpg_path], output)

        doc = fitz.open(output)
        assert doc.page_count == 2
        doc.close()

    def test_single_image(self, jpg_path: Path, tmp_path: Path) -> None:
        """单张图片合并后为单页 PDF。"""
        import fitz

        output = tmp_path / "single.pdf"
        images_to_pdf([jpg_path], output)

        doc = fitz.open(output)
        assert doc.page_count == 1
        doc.close()


class TestSplitPdf:
    """测试 split_pdf：将 PDF 拆解为图片列表和页码标签。"""

    def test_all_pages(self, pdf_path: Path) -> None:
        """不指定页码范围则返回全部页。"""
        images, labels = split_pdf(pdf_path, None)
        assert len(images) > 0
        assert len(images) == len(labels)
        # 标签为 1-based
        assert labels[0] == 1
        for img in images:
            assert img.suffix == ".png"
            assert img.exists()

    def test_specific_pages(self, pdf_path: Path) -> None:
        """指定页码范围只返回对应页。"""
        images, labels = split_pdf(pdf_path, "1")
        assert len(images) == 1
        assert labels == [1]

    def test_page_range(self, pdf_path: Path) -> None:
        """页码范围正确拆分。"""
        images, labels = split_pdf(pdf_path, "1-1")
        assert len(images) == 1
        assert labels == [1]

    def test_labels_are_1_based(self, pdf_path: Path) -> None:
        """页码标签为 1-based。"""
        images, labels = split_pdf(pdf_path, "1")
        assert labels[0] == 1

    def test_invalid_page_range(self, pdf_path: Path) -> None:
        """页码范围越界抛出 ValueError。"""
        with pytest.raises(ValueError, match="越界"):
            split_pdf(pdf_path, "999")
