# CLI 命令行参数优化设计

## 概述

简化 CLI 参数设计，将 `input` 位置参数和 `-d/--input-dir` 标志合并为单一的 `input` 位置参数，自动判断文件/目录，同时严格限制目录下只能有一种类型的文件（全图片或全 PDF），混合直接报错。

## CLI 参数

### 新参数列表

```
python main.py <path> [--model MODEL] [--pages PAGES] [--api-key KEY] [--ollama-url URL]
```

### 与当前对比

| 参数 | 当前 | 新设计 |
|------|------|--------|
| `input` | 位置参数，可选 | 位置参数，**必填** |
| `-d` / `--input-dir` | 可选标志 | **移除** |
| `--model` | 同 | 不变 |
| `--pages` | 同 | 不变（规则调整见下） |
| `--api-key` | 同 | 不变 |
| `--ollama-url` | 同 | 不变 |

### `<path>` 判断逻辑

```
路径不存在 → 报错退出
路径是文件 → 单文件模式（自动判断图片/PDF）
路径是目录 → 批量模式 → 扫描目录判断类型
```

### `--pages` 行为

| 模式 | `--pages` 行为 |
|------|---------------|
| 单文件图片 | 报错退出（图片不支持页码范围） |
| 单文件 PDF | 生效，过滤页码 |
| 批量模式 | 打印警告，忽略 `--pages`，继续执行 |

## 引擎与文件格式适配

不同引擎的原生能力不同，系统自动在格式间转换：

### 引擎能力矩阵

| 引擎 | `parse_image()` (图片识别) | `parse_pdf()` (PDF 直接解析) |
|------|---------------------------|---------------------------|
| liteparse | ❌ 不支持 | ✅ 支持 |
| siliconflow | ✅ 支持 | ❌ 不支持 |
| ollama | ✅ 支持 | ❌ 不支持 |

### 单文件模式下的自动转换

| 输入类型 | liteparse | 其他引擎 (siliconflow/ollama) |
|---------|----------|---------------------------------------|
| 图片 | 转为单页 PDF → `parse_pdf()` | 直接 `parse_image()` |
| PDF | 直接 `parse_pdf()` | 拆为图片 → `parse_image()` 逐页识别 |

### 批量模式下的自动转换

| 输入类型 | liteparse | 其他引擎 (siliconflow/ollama) |
|---------|----------|---------------------------------------|
| 图片目录 | 合并为 PDF → `parse_pdf()` | 逐张 `parse_image()` → 合并输出 |
| PDF 目录 | 逐文件 `parse_pdf()` | 逐文件拆为图片 → `parse_image()` 逐页识别 |

## 目录类型检测

### 扫描规则 (`batch.py` `_collect_files`)

目录扫描严格互斥：

```
扫描目录下所有文件 →
  全是图片 (.png/.jpg/.jpeg) → 图片批量模式
  全是 PDF  (.pdf)           → PDF 批量模式
  既有图片又有 PDF           → 报错退出，列出各类型文件数量
  没有任何支持的文件          → 报错退出
```

### 错误信息示例

```
错误: 目录中包含混合文件类型（图片和 PDF），请确保目录下只有一种类型的文件。
  图片: 3 个 (.png/.jpg/.jpeg)
  PDF:  2 个 (.pdf)
```

### 处理分支（无混合情况）

| 目录内容 | liteparse 引擎 | 其他引擎 |
|---------|---------------|---------|
| 仅有图片 | 图片合并为临时 PDF → LiteParse 解析 | 图片批量流程（合并输出） |
| 仅有 PDF | PDF 批量流程（各自输出） | PDF 批量流程（各自输出） |

### 输出规则（不变）

| 场景 | 输出文件 | 位置 |
|------|---------|------|
| 图片批量 | `目录名.md` | 输入目录的同级 |
| PDF 批量 | 各 `文件名.md` | 各 PDF 同目录 |
| 图片→PDF→LiteParse | `目录名.md` | 输入目录的同级 |

## 错误处理

在现有错误处理基础上，新增/调整以下场景：

| 场景 | 行为 |
|------|------|
| `<path>` 未提供 | argparse 报错退出 |
| `<path>` 不存在 | 报错退出 |
| 目录混合文件类型 | 报错退出，列出图片/PDF 数量 |
| 目录无支持文件 | 报错退出 |
| 批量模式 + `--pages` | 打印警告，忽略 `--pages`，继续执行 |
| 单文件图片 + `--pages` | 报错退出（图片不支持页码） |
| `-d` / `--input-dir` 已移除 | argparse 报 "unrecognized arguments"（向后兼容提醒） |

其他错误处理逻辑不变：文件格式不支持、API Key 缺失、API 调用失败等保持现有行为。

## 涉及文件

| 文件 | 改动 |
|------|------|
| `main.py` | `input` 改为必填；移除 `-d/--input-dir`；`<path>` 自动判断文件/目录；`--pages` 行为调整 |
| `batch.py` | `_collect_files` 改为严格互斥检测，混合目录报错；移除混合目录的分发逻辑；`recognize()` → `parse_image()` |
| `ocr.py` | `recognize()` → `parse_image()` 调用更新 |
| `engines/base.py` | `recognize()` 重命名为 `parse_image()` |
| `engines/siliconflow.py` | `recognize()` 重命名为 `parse_image()` |
| `engines/ollama.py` | `recognize()` 重命名为 `parse_image()` |
| `engines/liteparse.py` | `recognize()` → `parse_image()` 或抛出 NotImplementedError（如有实现） |
| `tests/test_batch.py` | 新增混合目录报错测试；更新对应测试用例；`recognize()` → `parse_image()` |
| `tests/test_engines.py` | `recognize()` → `parse_image()` 调用更新 |
| `tests/test_ocr.py` | `<path>` 未提供 → argparse 报错；单文件图片 + `--pages` → 报错；批量模式 + `--pages` → 警告提示；文件/目录自动判断验证 |

## 测试

- `tests/test_batch.py`：
  - 混合目录（图片+PDF）→ 报错，错误信息包含文件类型数量
  - 空目录（无支持文件）→ 报错
  - 纯图片目录 → 正常处理
  - 纯 PDF 目录 → 正常处理
- `tests/test_ocr.py`：
  - `<path>` 未提供 → argparse 报错
  - 单文件图片 + `--pages` → 报错
  - 批量模式 + `--pages` → 警告提示，继续执行
  - 文件、目录自动判断验证
