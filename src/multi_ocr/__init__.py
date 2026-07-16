"""Multi-OCR: 多引擎 OCR 工具包。

同时支持 CLI 工具和 SDK 依赖包两种使用方式。

CLI 使用:
    multi-ocr <path> [--model MODEL] [--pages PAGES]

SDK 使用:
    from multi_ocr import get_engine, ocr_file, OCREngine

    engine = get_engine("siliconflow", "deepseek-ai/DeepSeek-OCR", api_key="...")
    result = ocr_file(Path("mydoc.pdf"), engine)
"""

from multi_ocr.engines import get_engine
from multi_ocr.engines.base import OCREngine
from multi_ocr.single import ocr_file
from multi_ocr.batch import ocr_directory

__all__ = [
    "get_engine",
    "OCREngine",
    "ocr_file",
    "ocr_directory",
]

__version__ = "0.2.2"
