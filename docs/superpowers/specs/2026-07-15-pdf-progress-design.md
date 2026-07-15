# PDF 处理进度条 设计文档

## 概述

为 PDF/图片 OCR 处理增加 tqdm 进度条显示。单文件 PDF 显示逐页进度，批量 PDF 逐个文件显示各自页进度，批量图片合并显示一条总进度。同时将三个 API 引擎中重复的 `parse_pdf()` 逐页迭代逻辑提取到基类。

## 背景

当前 `ocr_file()` 对 PDF 逐页调用 OCR API 时没有任何进度提示。批量模式仅有文件级 tqdm，不显示页级进度。三个引擎（SiliconFlow / DashScope / Ollama）各自实现了完全相同的 `parse_pdf()` 逐页迭代逻辑。

## 各模式进度行为

| 模式 | 进度条 | 示例 |
|------|--------|------|
| 单文件 PDF | 逐页 | `识别 report.pdf: 50%\|█████▌ \| 5/10 [00:25<00:25]` |
| 单文件图片 | 无（单张瞬间完成） | — |
| 批量 PDF | 逐个文件，各自显示页进度 | `识别 a.pdf: 100%\|████\| 5/5` → `识别 b.pdf: 60%\|██▌ \| 6/10` |
| 批量图片 | 所有图片合并一条 | `识别 dir_name: 60%\|██▌ \| 3/5 [00:15<00:10]` |

关键原则：不需要预扫描，打开文件时获取页数即创建 tqdm。批量 PDF 下，前一个文件完成后 bar 自然消失，下一个文件 bar 出现。

## 改动范围

### 1. `engines/base.py` — 基类提供默认 parse_pdf 实现

- `parse_pdf` 从 `@abstractmethod` 改为普通方法，提供默认逐页实现
- 新增 `progress_callback: Callable[[], None] | None = None` 参数
- 新增 `from typing import Callable`、`import shutil`、`from pdf_utils import split_pdf`
- 方法体：`split_pdf()` → 逐页 `parse_image()` → 每页调用 `progress_callback()` → 合并结果

### 2. `engines/siliconflow.py` / `dashscope.py` / `ollama.py` — 删除重复代码

- 删除各自的 `parse_pdf()` 方法（每个约 12 行）
- 删除不再需要的 `import shutil` 和 `from pdf_utils import split_pdf`
- 其余代码不变，继承基类默认实现

### 3. `engines/liteparse.py` — 签名兼容

- `parse_pdf()` 签名加上 `progress_callback=None` 参数，方法体不变
- LiteParse 原生调用不支持逐页回调，进度条在调用完成后一次性更新

### 4. `single.py` — ocr_file 负责创建进度条

- PDF 处理：用 `fitz.open()` 获取页数（考虑 `--pages` 过滤后的实际页数），创建 tqdm，通过 `progress_callback` 传给 `engine.parse_pdf()`
- 图片处理：无进度条（单张瞬间完成）
- tqdm desc 格式：`识别 {文件名}`

### 5. `batch.py` — 简化，委托给 ocr_file

- `_batch_pdfs()`：移除 tqdm 包装，直接循环调用 `ocr_file()`，让 `ocr_file()` 自己管理进度条
- `_batch_images()`：保持现有 tqdm 用法，desc 为 `识别 {目录名}`

### 6. `main.py` — 无改动

## 非改动范围

- `pdf_utils.py` 不增加进度条（PDF 渲染通常很快，不是瓶颈）
- `main.py` 不引入新 CLI 参数
- `pyproject.toml` 不新增依赖（tqdm 已在 `batch.py` 中使用，说明已安装）

## 边界情况

- `--pages` 过滤：`ocr_file()` 需解析页码范围以获取实际处理页数，用于 tqdm 的 total 值
- LiteParse PDF：无逐页回调，进度条在 `parse_pdf` 返回后一次性 `update(total)`，表现为瞬间完成
- PDF 0 页：`fitz.open()` 返回 page_count=0，不创建进度条，直接返回空结果
- 异常中断：tqdm 随函数异常传播自然结束，无需手动 close（但建议加 try/finally 确保 close）

## 依赖

| 操作 | 包 | 用途 |
|------|-----|------|
| 已有 | `tqdm` | 终端进度条（`batch.py` 已使用） |
| 已有 | `fitz` (pymupdf) | 获取 PDF 页数（`pdf_utils.py` 已使用） |
