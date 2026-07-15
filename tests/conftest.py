from collections.abc import Generator
from pathlib import Path

import pytest

from engines.base import OCREngine
from pdf_utils import split_pdf
import shutil

TESTS_DIR = Path(__file__).parent


class MockEngine(OCREngine):
    """模拟 OCR 引擎，返回固定文本。"""

    def __init__(self, text: str = "mock ocr result") -> None:
        self._text = text

    def parse_image(self, image_path: Path) -> str:
        return f"{self._text} [{image_path.name}]"

    def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
        image_paths, page_labels = split_pdf(pdf_path, pages)
        try:
            results = []
            for img_path, label in zip(image_paths, page_labels):
                text = self.parse_image(img_path)
                results.append(f"--- 第 {label} 页 ---\n{text}")
            return "\n\n".join(results)
        finally:
            if image_paths:
                shutil.rmtree(image_paths[0].parent, ignore_errors=True)


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
