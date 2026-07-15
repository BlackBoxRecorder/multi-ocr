"""Multi-OCR: 将 PDF 和图片转换为 markdown 文档。

支持多种 OCR 引擎:
- SiliconFlow（DeepSeek-OCR / PaddleOCR-VL-1.5）
- DashScope（Qwen-VL-OCR）
- LiteParse（本地 PDF 解析）
- Ollama（本地 DeepSeek-OCR）

用法:
    python main.py <path> [--model MODEL] [--pages PAGES] [--api-key KEY] [--ollama-url URL]

    <path> 可以是文件或目录：
    - 文件：单文件模式，自动判断图片/PDF
    - 目录：批量模式，目录下只能有一种类型的文件（全图片或全 PDF）
"""

import argparse
import os
import sys
from pathlib import Path

from engines import get_engine
from single import ocr_file
from batch import ocr_directory

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
    "dashscope-qwen-vl-ocr": ("dashscope", "qwen-vl-ocr", "DashScope + Qwen-VL-OCR"),
    "liteparse": ("liteparse", "", "LiteParse (本地 PDF 解析)"),
    "ollama-deepseek-ocr": (
        "ollama",
        "deepseek-ocr:latest",
        "Ollama + DeepSeek-OCR",
    ),
}

# provider -> 环境变量名
_PROVIDER_ENV: dict[str, str] = {
    "siliconflow": "SILICONFLOW_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    # ollama / liteparse 为本地引擎，不需要 API Key
}


def _get_api_key(provider: str, cli_key: str | None) -> str | None:
    """获取 API Key：命令行 > provider 专用环境变量。
    Ollama / LiteParse 无需 API Key，返回空字符串。
    """
    if cli_key:
        return cli_key
    if provider in ("liteparse", "ollama"):
        return ""  # 本地引擎，无需 API Key
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
        help="输入文件路径（PDF 或图片）或目录路径（批量处理）",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=_build_model_help(),
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="页码范围，如 1-3,5（仅对单文件 PDF 有效）",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help=_build_api_key_help(),
    )
    parser.add_argument(
        "--ollama-url",
        default=None,
        help="Ollama 服务地址（默认读取 OLLAMA_BASE_URL 环境变量，都没有则用 http://127.0.0.1:11434）",
    )
    parser.add_argument(
        "-j",
        "--concurrency",
        type=int,
        default=1,
        help="并发数量（默认: 1，即串行处理）",
    )
    args = parser.parse_args()

    input_path: Path = args.input

    # 校验路径存在
    if not input_path.exists():
        print(f"错误: 路径不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 判断模式：目录 → 批量，文件 → 单文件
    batch_mode = input_path.is_dir()

    # --pages 约束
    pages: str | None = args.pages
    if batch_mode and pages:
        print("⚠️  --pages 在批量模式下忽略", file=sys.stderr)
        pages = None

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

    # API Key：命令行 > 环境变量（Ollama / LiteParse 跳过）
    api_key = _get_api_key(provider, args.api_key)
    if not api_key and provider not in ("liteparse", "ollama"):
        env_var = _PROVIDER_ENV.get(provider, "")
        print(
            f"请设置 {env_var} 环境变量或使用 --api-key 参数。",
            file=sys.stderr,
        )
        sys.exit(1)

    # 获取 Ollama base_url（仅 ollama 引擎使用）
    ollama_url = args.ollama_url or os.environ.get("OLLAMA_BASE_URL")

    # 并发数
    concurrency: int = args.concurrency
    if concurrency < 1:
        print("错误: --concurrency 必须 >= 1", file=sys.stderr)
        sys.exit(1)

    # 获取引擎
    try:
        engine = get_engine(
            provider=provider,
            model=model_name,
            api_key=api_key,
            base_url=ollama_url if provider == "ollama" else None,
        )
    except ValueError as e:
        print(f"引擎初始化失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 执行 OCR
    try:
        if batch_mode:
            ocr_directory(
                input_dir=input_path,
                engine=engine,
                concurrency=concurrency,
            )
        else:
            ocr_file(
                input_path=input_path,
                engine=engine,
                pages=pages,
                concurrency=concurrency,
            )
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
