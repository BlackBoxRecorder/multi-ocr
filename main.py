"""Multi-OCR: 将 PDF 和图片转换为文字。

支持 SiliconFlow（DeepSeek-OCR / PaddleOCR-VL-1.5）、
DashScope（Qwen-OCR: qwen3.5-ocr 等）多种 OCR 引擎。
"""

import argparse
import os
import sys
from pathlib import Path

from engines import get_engine
from ocr import ocr_file

DEFAULT_MODEL = "silicon-deepseek-ocr"

# --model 缩写 → (provider, model_name, description)
MODEL_MAP: dict[str, tuple[str, str, str]] = {
    "silicon-deepseek-ocr": (
        "siliconflow",
        "deepseek-ai/DeepSeek-OCR",
        "SiliconFlow + DeepSeek-OCR",
    ),
    "silicon-paddle-ocr": (
        "siliconflow",
        "PaddlePaddle/PaddleOCR-VL-1.5",
        "SiliconFlow + PaddleOCR-VL-1.5",
    ),
    "dashscope-qwen-ocr": ("dashscope", "qwen3.5-ocr", "DashScope + Qwen-OCR"),
    "dashscope-qwen-vl-ocr": ("dashscope", "qwen-vl-ocr", "DashScope + Qwen-VL-OCR"),
}

# provider -> 环境变量名
_PROVIDER_ENV: dict[str, str] = {
    "siliconflow": "SILICONFLOW_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
}


def _get_api_key(provider: str, cli_key: str | None) -> str | None:
    """获取 API Key：命令行 > provider 专用环境变量。"""
    if cli_key:
        return cli_key
    env_var = _PROVIDER_ENV[provider]
    return os.environ.get(env_var)


def _build_model_help() -> str:
    """动态生成 --model 参数的帮助文本。"""
    lines = [f"模型缩写（默认: {DEFAULT_MODEL}）\n可用模型:"]
    for alias, (_prov, _model, desc) in MODEL_MAP.items():
        lines.append(f"  {alias:<25} → {desc}")
    return "\n".join(lines)


def _build_api_key_help() -> str:
    """动态生成 --api-key 参数的帮助文本。"""
    lines = ["API Key（根据 --model 自动读取对应环境变量）:"]
    for provider, env_var in _PROVIDER_ENV.items():
        lines.append(f"  {provider} 模型 → {env_var}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 PDF 或图片转换为文字。默认使用 SiliconFlow + DeepSeek-OCR。",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="输入文件路径（PDF 或图片）",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=_build_model_help(),
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="页码范围，如 1-3,5（仅对 PDF 有效）",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help=_build_api_key_help(),
    )
    args = parser.parse_args()

    # 解析 --model 缩写 → provider + model_name
    entry = MODEL_MAP.get(args.model)
    if entry is None:
        valid = ", ".join(MODEL_MAP.keys())
        print(
            f"无效的 --model 值 '{args.model}'，可用: {valid}",
            file=sys.stderr,
        )
        sys.exit(1)
    provider, model_name, _desc = entry

    # API Key：命令行 > 环境变量
    api_key = _get_api_key(provider, args.api_key)
    if not api_key:
        env_var = _PROVIDER_ENV.get(provider, "")
        print(
            f"请设置 {env_var} 环境变量或使用 --api-key 参数。",
            file=sys.stderr,
        )
        sys.exit(1)

    # 获取引擎
    try:
        engine = get_engine(
            provider=provider,
            model=model_name,
            api_key=api_key,
        )
    except ValueError as e:
        print(f"引擎初始化失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 执行 OCR
    try:
        ocr_file(
            input_path=args.input,
            engine=engine,
            pages=args.pages,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
