"""Multi-OCR: 将 PDF 和图片转换为文字。

支持 SiliconFlow API 的 DeepSeek-OCR / PaddleOCR-VL-1.5 等模型。
"""

import argparse
import os
import sys
from pathlib import Path

from engines import get_engine
from ocr import ocr_file

DEFAULT_PROVIDER = "siliconflow"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-OCR"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 PDF 或图片转换为文字。默认使用 SiliconFlow + DeepSeek-OCR。"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="输入文件路径（PDF 或图片）",
    )
    parser.add_argument(
        "--provider",
        default=DEFAULT_PROVIDER,
        help=f"OCR 服务提供商（默认: {DEFAULT_PROVIDER}）",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"模型名称（默认: {DEFAULT_MODEL}）",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="页码范围，如 1-3,5（仅对 PDF 有效）",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API Key（默认读取 SILICONFLOW_API_KEY 环境变量）",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        default=False,
        help="输出到终端而非保存文件",
    )

    args = parser.parse_args()

    # API Key：命令行 > 环境变量
    api_key = args.api_key or os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        print(
            "请设置 SILICONFLOW_API_KEY 环境变量或使用 --api-key 参数。",
            file=sys.stderr,
        )
        sys.exit(1)

    # 获取引擎
    try:
        engine = get_engine(
            provider=args.provider,
            model=args.model,
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
            stdout=args.stdout,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
