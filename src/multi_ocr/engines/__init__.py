from multi_ocr.engines.base import OCREngine
from multi_ocr.engines.ollama import OllamaEngine
from multi_ocr.engines.siliconflow import SiliconFlowEngine

# LiteParse 为可选依赖，仅在已安装时注册
try:
    from multi_ocr.engines.liteparse import LiteParseEngine

    _HAS_LITEPARSE = True
except ImportError:
    _HAS_LITEPARSE = False

# 引擎注册表：provider 名 -> Engine 类
# 添加新提供商时只需在此注册
_registry: dict[str, type[OCREngine]] = {
    "ollama": OllamaEngine,
    "siliconflow": SiliconFlowEngine,
}

if _HAS_LITEPARSE:
    _registry["liteparse"] = LiteParseEngine


def get_engine(
    provider: str, model: str, api_key: str, base_url: str | None = None, **extra_kwargs
) -> OCREngine:
    """工厂函数：按 provider 名查找并实例化 OCR 引擎。

    Args:
        provider: OCR 服务提供商名称（如 "siliconflow"）。
        model: 模型名称（如 "deepseek-ai/DeepSeek-OCR"）。
        api_key: API 密钥。
        base_url: 自定义 API 地址（当前仅 ollama 引擎使用）。

    Returns:
        OCREngine 实例。

    Raises:
        ValueError: 如果 provider 未注册。
    """
    engine_cls = _registry.get(provider)
    if engine_cls is None:
        available = ", ".join(_registry.keys())
        raise ValueError(f"未知的 OCR 提供商: {provider}，当前可用: {available}")
    kwargs: dict = dict(extra_kwargs)
    if base_url is not None:
        kwargs["base_url"] = base_url
    return engine_cls(model=model, api_key=api_key, **kwargs)
