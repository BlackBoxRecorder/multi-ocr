# Concurrency Design

## Summary

新增 `-j N` / `--concurrency N` CLI 参数，使用 `ThreadPoolExecutor` 在三个处理层面引入并发，加快批量 OCR API 调用速度。默认值为 1，保持向后兼容。

## Motivation

当前所有 OCR 处理均为串行：批量图片逐张调用 API、批量 PDF 逐个处理、PDF 内多页逐页调用 API。对于 I/O 密集型的 API 调用场景，并发化可显著缩短总耗时。例如 10 张图片每张 3 秒，串行需 30 秒，-j 5 仅需约 6 秒。

## Design Decisions

- **并发机制**：`concurrent.futures.ThreadPoolExecutor`，不改引擎接口签名，I/O 等待时 GIL 自然释放
- **参数名**：`-j N`（短参数）/ `--concurrency N`（长参数），模仿 make 风格
- **默认值**：1（不并发，保持现有行为）
- **覆盖范围**：全部场景（批量图片、批量 PDF、单 PDF 多页）

## Architecture

### 参数传递链路

```
main.py  -j 4
  │
  ├─ 单文件 → ocr_file(input_path, engine, pages, concurrency=4)
  │               └─ engine.parse_pdf(pdf_path, pages, callback, concurrency=4)
  │                      └─ base.py OCREngine.parse_pdf() 默认实现中使用线程池
  │
  └─ 批量   → ocr_directory(input_dir, engine, concurrency=4)
                  ├─ _batch_images(input_dir, images, engine, concurrency=4)
                  │      └─ ThreadPoolExecutor 并发多图
                  └─ _batch_pdfs(pdfs, engine, concurrency=4)
                         └─ ThreadPoolExecutor 并发多 PDF，内部调 ocr_file()
```

### 三个并发注入点

| 文件 | 函数 | 并发粒度 | 当前行为 | 改动后 |
|------|------|---------|---------|--------|
| `engines/base.py` | `OCREngine.parse_pdf()` 默认实现 | PDF 页 | `for` 循环逐页 `parse_image()` | `ThreadPoolExecutor` 并发多页 |
| `batch.py` | `_batch_images()` | 图片文件 | `for` 循环逐张 `parse_image()` | `ThreadPoolExecutor` 并发多图 |
| `batch.py` | `_batch_pdfs()` | PDF 文件 | `for` 循环逐个 `ocr_file()` | `ThreadPoolExecutor` 并发多 PDF |

## Implementation Details

### 并发执行模式

每个注入点使用统一模式：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=concurrency) as executor:
    future_to_idx = {
        executor.submit(func, item): idx
        for idx, item in enumerate(items)
    }
    results = [None] * len(items)
    for future in tqdm(as_completed(future_to_idx), total=len(items), desc="..."):
        idx = future_to_idx[future]
        results[idx] = future.result()  # 异常在这里抛出
```

- `as_completed` + 索引映射保证结果顺序
- `tqdm` 实时显示进度
- 任一任务失败时，`future.result()` 抛出异常，`with` 退出时自动等待剩余任务完成并清理

### 引擎线程安全

- API 引擎（SiliconFlow、DashScope、Ollama）：HTTP 客户端 `OpenAI` 实例本身是线程安全的，多个线程共享同一引擎实例并发调用 `parse_image()` 没有问题
- LiteParse：该引擎覆盖了 `parse_pdf()`，不走默认逐页实现，因此不受并发改动影响

### 特殊情况处理

| 情况 | 行为 |
|------|------|
| `concurrency=1` | 等效于现有串行行为（但走线程池路径，仅 1 个 worker） |
| LiteParse 单 PDF | parse_pdf 被子类覆盖，不使用默认实现，concurrency 参数被忽略 |
| LiteParse 批量 PDF | _batch_pdfs 中并发多个 ocr_file() 调用，每个内部走 LiteParse 原生解析 |
| `--pages` 指定页码 + 并发 | parse_pdf 默认实现仅对指定页并发，页数少时效果有限但不报错 |

### API 限流风险

并发调用可能触发 API 提供商的速率限制（Rate Limit）。此项作为使用者的自主选择，工具本身不做限流控制。若遇 429 错误，用户应降低并发数重试。

## CLI Changes

`main.py` 新增参数：

```
-j N, --concurrency N    并发数量（默认: 1，即串行处理）
```

用法示例：

```bash
# 批量处理图片目录，4 并发
python main.py ./images -j 4

# 单 PDF 多页，8 并发
python main.py report.pdf -j 8 --pages 1-50

# 不指定，默认串行（行为不变）
python main.py ./images
```

## Function Signature Changes

仅需在以下函数签名中新增 `concurrency` 参数：

| 文件 | 函数 | 新增参数 |
|------|------|---------|
| `batch.py` | `ocr_directory()` | `concurrency: int = 1` |
| `batch.py` | `_batch_images()` | `concurrency: int = 1` |
| `batch.py` | `_batch_pdfs()` | `concurrency: int = 1` |
| `single.py` | `ocr_file()` | `concurrency: int = 1` |
| `engines/base.py` | `OCREngine.parse_pdf()` | `concurrency: int = 1` |
| `main.py` | `main()` | 解析 `-j` 参数并向下传递 |

引擎子类（SiliconFlow、DashScope、Ollama）**无需修改**，仅有 LiteParse 覆盖了 `parse_pdf()` 签名，需补上 `concurrency` 参数以保持兼容（内部忽略该参数）。

## Testing

- `tests/test_batch.py`：新增并发图片/PDF 批量测试（mock engine），验证结果顺序、异常传递
- `tests/test_engines.py`：新增 `parse_pdf` 默认实现并发测试，验证多页并发结果正确
- `tests/test_single.py`：验证 `concurrency` 参数传递无误
- 所有现有测试应保持通过
