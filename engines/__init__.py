from engines.base import OCREngine
from engines.dashscope import DashScopeEngine
from engines.siliconflow import SiliconFlowEngine

# 引擎注册表：provider 名 -> Engine 类
# 添加新提供商时只需在此注册
_registry: dict[str, type[OCREngine]] = {
    "dashscope": DashScopeEngine,
    "siliconflow": SiliconFlowEngine,
}


def get_engine(provider: str, model: str, api_key: str) -> OCREngine:
    """工厂函数：按 provider 名查找并实例化 OCR 引擎。

    Args:
        provider: OCR 服务提供商名称（如 "siliconflow"）。
        model: 模型名称（如 "deepseek-ai/DeepSeek-OCR"）。
        api_key: API 密钥。

    Returns:
        OCREngine 实例。

    Raises:
        ValueError: 如果 provider 未注册。
    """
    engine_cls = _registry.get(provider)
    if engine_cls is None:
        available = ", ".join(_registry.keys())
        raise ValueError(f"未知的 OCR 提供商: {provider}，当前可用: {available}")
    return engine_cls(model=model, api_key=api_key)
