"""测试 engines 模块：引擎工厂函数。"""

import pytest

from engines import get_engine


class TestGetEngine:
    """测试 get_engine 工厂函数。"""

    def test_known_provider_siliconflow(self) -> None:
        engine = get_engine(
            provider="siliconflow", model="test-model", api_key="test-key"
        )
        from engines.siliconflow import SiliconFlowEngine

        assert isinstance(engine, SiliconFlowEngine)
        assert engine._model == "test-model"

    def test_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="未知的 OCR 提供商"):
            get_engine(provider="nonexistent", model="m", api_key="k")
