"""测试 engines 模块：引擎工厂函数。"""

from pathlib import Path

import pytest

from multi_ocr.engines import _HAS_LITEPARSE, get_engine


class TestGetEngine:
    """测试 get_engine 工厂函数。"""

    def test_known_provider_siliconflow(self) -> None:
        engine = get_engine(
            provider="siliconflow", model="test-model", api_key="test-key"
        )
        from multi_ocr.engines.siliconflow import SiliconFlowEngine

        assert isinstance(engine, SiliconFlowEngine)
        assert engine._model == "test-model"

    def test_known_provider_dashscope(self) -> None:
        engine = get_engine(
            provider="dashscope", model="qwen-vl-ocr", api_key="test-key"
        )
        from multi_ocr.engines.dashscope import DashScopeEngine

        assert isinstance(engine, DashScopeEngine)
        assert engine._model == "qwen-vl-ocr"

    def test_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="未知的 OCR 提供商"):
            get_engine(provider="nonexistent", model="m", api_key="k")

    @pytest.mark.skipif(not _HAS_LITEPARSE, reason="liteparse 未安装")
    def test_known_provider_liteparse(self) -> None:
        engine = get_engine(provider="liteparse", model="", api_key="")
        from multi_ocr.engines.liteparse import LiteParseEngine

        assert isinstance(engine, LiteParseEngine)
        assert engine._model == ""
        assert engine._api_key == ""


# ---------------------------------------------------------------------------
# parse_pdf Concurrency Tests
# ---------------------------------------------------------------------------


class TestParsePdfConcurrency:
    """测试 OCREngine.parse_pdf 默认实现的并发行为。"""

    def test_concurrent_pages_ordered(self, tmp_path: Path) -> None:
        """并发模式下结果按页码顺序排列。"""
        from multi_ocr.engines.base import OCREngine

        class TestEngine(OCREngine):
            def parse_image(self, image_path: Path) -> str:
                return f"content of {image_path.name}"

        # 创建多页 PDF
        import fitz

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        for _ in range(3):
            doc.new_page()
        doc.save(pdf_path)
        doc.close()

        engine = TestEngine()
        result = engine.parse_pdf(pdf_path, concurrency=2)

        # 验证三页都在结果中，且顺序正确
        assert "第 1 页" in result
        assert "第 2 页" in result
        assert "第 3 页" in result
        idx1 = result.index("第 1 页")
        idx2 = result.index("第 2 页")
        idx3 = result.index("第 3 页")
        assert idx1 < idx2 < idx3

    def test_concurrency_1_same_as_sequential(self, tmp_path: Path) -> None:
        """concurrency=1 结果与串行一致。"""
        from multi_ocr.engines.base import OCREngine

        call_order: list[str] = []

        class OrderTrackingEngine(OCREngine):
            def parse_image(self, image_path: Path) -> str:
                call_order.append(image_path.name)
                return f"ok {image_path.name}"

        import fitz

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        for _ in range(3):
            doc.new_page()
        doc.save(pdf_path)
        doc.close()

        engine = OrderTrackingEngine()
        engine.parse_pdf(pdf_path, concurrency=1)
        # 串行时调用顺序应与页码一致
        assert len(call_order) == 3
        assert call_order == sorted(call_order)

    def test_single_page_with_high_concurrency(self, tmp_path: Path) -> None:
        """单页 PDF + 高并发数不应报错。"""
        from multi_ocr.engines.base import OCREngine

        class TestEngine(OCREngine):
            def parse_image(self, image_path: Path) -> str:
                return "single page"

        import fitz

        pdf_path = tmp_path / "single.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(pdf_path)
        doc.close()

        engine = TestEngine()
        result = engine.parse_pdf(pdf_path, concurrency=10)
        assert "single page" in result
