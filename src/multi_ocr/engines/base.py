import shutil
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from multi_ocr.pdf_utils import split_pdf


class OCREngine(ABC):
    """OCR 引擎抽象基类。所有 OCR 引擎必须实现此接口。"""

    def merge_results(self, results: list[str]) -> str:
        """合并多条返回结果。默认用双换行分隔，JSON 引擎可覆写为数组格式。"""
        return "\n\n".join(results)

    @abstractmethod
    def parse_image(self, image_path: Path) -> str:
        """对单张图片进行 OCR，返回 markdown 文本。

        Args:
            image_path: 图片文件路径。

        Returns:
            识别出的 markdown 文本内容。
        """
        ...

    def parse_pdf(
        self,
        pdf_path: Path,
        pages: str | None = None,
        progress_callback: Callable[[], None] | None = None,
        concurrency: int = 1,
    ) -> str:
        """解析 PDF，返回 markdown 文本。

        默认实现：拆页 → 调用 parse_image() → 合并结果。
        子类可覆盖以提供原生 PDF 解析（如 LiteParse）。

        Args:
            pdf_path: PDF 文件路径。
            pages: 页码范围字符串（如 "1-3,5"），None 表示全部。
            progress_callback: 每处理完一页时调用（可选）。
            concurrency: 并发数，默认 1（串行），>1 时使用线程池并发处理多页。

        Returns:
            解析出的 markdown 文本内容。
        """
        image_paths, page_labels = split_pdf(pdf_path, pages)
        try:
            if concurrency > 1:
                results = self._parse_pages_concurrent(
                    image_paths, page_labels, concurrency, progress_callback
                )
            else:
                results = []
                for img_path, label in zip(image_paths, page_labels):
                    text = self.parse_image(img_path)
                    results.append(f"--- 第 {label} 页 ---\n{text}")
                    if progress_callback:
                        progress_callback()
            return self.merge_results(results)
        finally:
            if image_paths:
                shutil.rmtree(image_paths[0].parent, ignore_errors=True)

    def _parse_pages_concurrent(
        self,
        image_paths: list[Path],
        page_labels: list[int],
        concurrency: int,
        progress_callback: Callable[[], None] | None,
    ) -> list[str]:
        """并发解析多页图片，保持页码顺序。

        Args:
            image_paths: 图片路径列表。
            page_labels: 页码标签列表（1-based）。
            concurrency: 并发线程数。
            progress_callback: 每完成一页时调用（可选）。

        Returns:
            按页码顺序排列的结果列表，每项格式为 "--- 第 N 页 ---\n{text}"。
        """
        results: list[str | None] = [None] * len(image_paths)
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_idx = {
                executor.submit(self.parse_image, img_path): idx
                for idx, img_path in enumerate(image_paths)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                text = future.result()
                results[idx] = f"--- 第 {page_labels[idx]} 页 ---\n{text}"
                if progress_callback:
                    progress_callback()
        return [r for r in results if r is not None]
