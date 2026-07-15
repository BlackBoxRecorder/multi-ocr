# Batch Processing Design

## Summary

为 multi-ocr 新增批量处理能力：通过 `-d` / `--input-dir` 参数指定目录，支持批量处理图片（合并输出）和 PDF（各自输出），并提供 liteparse 引擎下图片自动合并为 PDF 再解析的特殊流程。

## Architecture

新增 `batch.py` 模块，将批量扫描、分发、合并输出等逻辑独立封装。`ocr.py` 保持单文件处理职责不变。`main.py` 成为编排层：根据是否传入 `-d` 参数分发到批量或单文件流程。

```
main.py (CLI 编排)
  ├─ 无 -d → ocr_file()          [ocr.py，现有逻辑]
  └─ 有 -d → ocr_directory()     [batch.py，新增]
                ├─ _collect_files()
                ├─ _batch_images()
                ├─ _batch_pdfs()         → 内部调用 ocr_file()
                └─ _images_to_pdf_and_parse()
                        └─ images_to_pdf()  [pdf_utils.py，新增]
```

## CLI Changes

`main.py` 新增 `-d` / `--input-dir` 参数，与 `input` 位置参数互斥（二选一）：

```
usage: multi-ocr [-h] [--model MODEL] [--pages PAGES] [--api-key API_KEY]
                 (input | -d INPUT_DIR)

单文件模式（现有，不变）:
  input                  输入文件路径（PDF 或图片）

批量模式（新增）:
  -d, --input-dir DIR    输入目录路径，批量处理目录下所有图片/PDF

通用参数（两种模式共享）:
  --model                 模型缩写（默认 silicon-deepseek-ocr）
  --pages                 页码范围，批量模式下忽略
  --api-key               API Key
```

## batch.py Module

暴露单一入口函数 `ocr_directory(input_dir, engine)`，内部流程：

### 1. 扫描目录 (`_collect_files`)

- 收集所有图片文件（`.png` / `.jpg` / `.jpeg`），按文件名排序
- 收集所有 PDF 文件（`.pdf`），按文件名排序
- 返回 `(images, pdfs)` 元组

### 2. 校验与分发

| 目录内容 | liteparse 引擎 | 其他引擎 |
|---------|---------------|---------|
| 仅有图片 | 走图片→PDF→LiteParse 流程 | 走图片批量流程 |
| 仅有 PDF | 走 PDF 批量流程 | 走 PDF 批量流程 |
| 混合（图片+PDF） | 报错退出 | 走图片批量流程 |
| 无支持文件 | ValueError | ValueError |
| 目录不存在 | FileNotFoundError | FileNotFoundError |

> 注：非 liteparse 引擎遇到混合目录时，直接按图片批量处理，忽略 PDF。理由是用户传入的 model 如果是支持图片的引擎，默认意图是处理图片。

### 3. 处理流程

**图片批量 (`_batch_images`)**：
- 遍历图片列表，逐张调用 `engine.recognize()`
- 每张结果用 `\n\n--- 第 N 张 ---\n\n` 分隔
- 合并所有结果，写入 `input_dir.md`（放在输入目录同级）

**PDF 批量 (`_batch_pdfs`)**：
- 遍历 PDF 列表，逐文件调用 `ocr_file()`（复用单文件逻辑，不传 `pages`）
- 每个 PDF 自动输出同名的 `.md` 文件

**图片→PDF→LiteParse (`_images_to_pdf_and_parse`)**：
- 调用 `pdf_utils.images_to_pdf()` 将排序后的图片合并为临时 PDF
- 调用 `engine.parse_pdf()` 获取 markdown 文本
- 写入 `input_dir.md`
- 清理临时 PDF

### 4. 输出

| 场景 | 输出文件 | 位置 |
|------|---------|------|
| 图片批量 | `目录名.md` | 输入目录的同级 |
| PDF 批量 | 各 `文件名.md` | 各 PDF 同目录 |
| 图片→PDF→LiteParse | `目录名.md` | 输入目录的同级 |

## pdf_utils.py Changes

新增函数：

```python
def images_to_pdf(image_paths: list[Path], output_path: Path) -> Path:
    """将多张图片按顺序合并为一个 PDF 文件。
    使用 pymupdf (fitz) 创建空白文档并逐张插入图片。
    """
```

## Progress Display

单层 tqdm 进度条，按处理单元数量显示：

| 场景 | 进度条含义 | 示例描述 |
|------|-----------|---------|
| 图片批量 | 图片总数 | `处理 images/ 目录: 12/12` |
| PDF 批量 | PDF 文件数 | `处理 pdfs/ 目录: 5/5` |
| 图片→PDF | 分两阶段 | 合并阶段打印提示，解析由 liteparse 自身输出 |

## Error Handling

遵循"立即中止"策略：
- 任何单文件/单图 OCR 失败 → 抛出异常，不继续
- 扫描阶段错误 → 立即报错退出
- 混合目录 + liteparse → 立即报错退出
- `main.py` 统一捕获并输出错误信息

## Testing

- **`tests/test_batch.py`**（新建）：
  - `_collect_files`：空目录、纯图片、纯 PDF、混合目录的扫描逻辑
  - `_batch_images`：合并输出内容、文件名正确性
  - `_batch_pdfs`：每个 PDF 生成对应 `.md` 文件
  - `_images_to_pdf_and_parse`：正确调用 `parse_pdf`，输出到正确路径
  - 混合目录 + liteparse → 报错
  - 目录不存在 / 无支持文件 → 报错
- **`tests/test_pdf_utils.py`**（追加）：`test_images_to_pdf`
- **`tests/test_ocr.py`**（不变）：现有测试保持通过
