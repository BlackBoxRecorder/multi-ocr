"""测试 engines 模块：引擎工厂函数。"""

import pytest

from engines import _HAS_LITEPARSE, get_engine


class TestGetEngine:
    """测试 get_engine 工厂函数。"""

    def test_known_provider_siliconflow(self) -> None:
        engine = get_engine(
            provider="siliconflow", model="test-model", api_key="test-key"
        )
        from engines.siliconflow import SiliconFlowEngine

        assert isinstance(engine, SiliconFlowEngine)
        assert engine._model == "test-model"

    def test_known_provider_dashscope(self) -> None:
        engine = get_engine(
            provider="dashscope", model="qwen-vl-ocr", api_key="test-key"
        )
        from engines.dashscope import DashScopeEngine

        assert isinstance(engine, DashScopeEngine)
        assert engine._model == "qwen-vl-ocr"

    def test_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="未知的 OCR 提供商"):
            get_engine(provider="nonexistent", model="m", api_key="k")

    @pytest.mark.skipif(not _HAS_LITEPARSE, reason="liteparse 未安装")
    def test_known_provider_liteparse(self) -> None:
        engine = get_engine(provider="liteparse", model="", api_key="")
        from engines.liteparse import LiteParseEngine

        assert isinstance(engine, LiteParseEngine)
        assert engine._model == ""
        assert engine._api_key == ""
