# 批量 PDF 模式：页面级并发支持

**日期**: 2026-07-15
**状态**: 已批准

## 问题

当前 `_batch_pdfs()` 的并发模式是文件级的：多个 PDF 之间并行，但每个 PDF 内部页面串行处理。当 PDF 数量少（如 2 个）但页数多时，`-j 10` 实际上只用到 2 路并发，大量 worker 闲置。

## 方案

**串行文件 × 页面级并发**：`_batch_pdfs()` 不再使用文件级线程池，改为串行遍历 PDF，每个 PDF 内部将 `concurrency` 传递给 `ocr_file()`，由底层 `OCREngine.parse_pdf()` 做页面级并发。

## 改动

**仅修改 `batch.py` 的 `_batch_pdfs()` 函数**（约 10 行变更）：

- 移除 `ThreadPoolExecutor` 文件级并发逻辑
- 串行循环中调用 `ocr_file(..., concurrency=concurrency)`
- `concurrency=1` 时串行逐页的自然行为保持不变

### 改动前

```python
def _batch_pdfs(pdfs, engine, concurrency=1):
    if concurrency > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(ocr_file, input_path=pdf_path, engine=engine, pages=None)
                for pdf_path in pdfs
            ]
            for future in as_completed(futures):
                future.result()
    else:
        for pdf_path in pdfs:
            ocr_file(input_path=pdf_path, engine=engine, pages=None)
```

### 改动后

```python
def _batch_pdfs(pdfs, engine, concurrency=1):
    for pdf_path in pdfs:
        ocr_file(input_path=pdf_path, engine=engine, pages=None, concurrency=concurrency)
```

## 不修改的模块

| 模块 | 原因 |
|---|---|
| `single.py` `ocr_file()` | 已有 `concurrency` 参数并传递 |
| `engines/base.py` | `parse_pdf()` / `_parse_pages_concurrent()` 已支持 |
| `engines/liteparse.py` | 已忽略 `concurrency` 参数，传了无副作用 |
| `main.py` | 单文件模式已在传 `concurrency` |
| `_batch_images()` | 图片并发逻辑与本次无关 |

## 行为影响

| 场景 | 改动前 | 改动后 |
|---|---|---|
| 2 PDF, `-j 10` | 2 路文件并发，每个 PDF 内串行 | PDF1 用满 10 并发 → PDF2 用满 10 并发 |
| 10 PDF, `-j 4` | 4 路文件并发，每个 PDF 内串行 | 每个 PDF 串行，各用 4 并发处理页面 |
| `-j 1`（默认） | 串行文件 + 串行页面 | **无变化** |

> **权衡说明**：当 PDF 数量多且页数少时，改后方案不如原来的文件级并发快。但实际场景中批量 PDF 通常来自同一份文档分拆（页数均匀），页面级并发是更通用的收益点。如果未来有大量短 PDF 的场景，可再考虑两阶段自适应调度。
