from collections.abc import Generator
from pathlib import Path

import pytest

from engines.base import OCREngine

TESTS_DIR = Path(__file__).parent


class MockEngine(OCREngine):
    """模拟 OCR 引擎，返回固定文本。"""

    def __init__(self, text: str = "mock ocr result") -> None:
        self._text = text

    def recognize(self, image_path: Path) -> str:
        return f"{self._text} [{image_path.name}]"


@pytest.fixture
def mock_engine() -> MockEngine:
    return MockEngine()


@pytest.fixture
def custom_engine() -> Generator[MockEngine, None, None]:
    yield MockEngine("custom text")


@pytest.fixture
def jpg_path() -> Path:
    return TESTS_DIR / "1.jpg"


@pytest.fixture
def pdf_path() -> Path:
    return TESTS_DIR / "2.pdf"
