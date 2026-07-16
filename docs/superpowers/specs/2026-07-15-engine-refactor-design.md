# 引擎接口重构设计文档

## 概述

重构引擎接口，强制每个引擎实现 `parse_image` 和 `parse_pdf` 两个抽象方法。将 PDF→图片 拆解逻辑从编排层（`ocr.py`）下沉到各引擎内部，同时将编排文件 `ocr.py` 重命名为 `single.py`，职责更清晰。

## 架构变化

### 现状

```
ocr_file() 中 PDF 分支:
  ├── try engine.parse_pdf() → 成功直接返回
  └── except NotImplementedError → pdf_to_images() → 逐页 parse_image() → 合并
```

编排层（`ocr.py`）既负责流程编排，又负责 PDF 拆图回退逻辑，耦合了引擎能力判断。

### 目标

```
ocr_file() 中:
  ├── PDF  → engine.parse_pdf()        # 引擎内部自行处理
  └── 图片 → engine.parse_image()
```

编排层只做分发，PDF 拆图逻辑全部在引擎内部。

## 模块结构

```
multi-ocr/
├── main.py              # CLI 入口（import 路径调整）
├── single.py            # ← 原 ocr.py，单文件处理
├── batch.py             # 目录批量处理（行为不变）
├── pdf_utils.py         # PDF 工具（新增 split_pdf）
├── engines/
│   ├── __init__.py      # 注册表 + get_engine()
│   ├── base.py          # OCREngine（parse_image + parse_pdf 均为 abstract）
│   ├── siliconflow.py   # + parse_pdf
│   ├── ollama.py        # + parse_pdf
│   └── liteparse.py     # 不变
└── tests/
    ├── test_single.py   # ← 原 test_ocr.py
    ├── test_batch.py    # import 调整
    └── test_engines.py  # 新增 parse_pdf 测试
```

## 引擎接口 (`engines/base.py`)

```python
class OCREngine(ABC):
    @abstractmethod
    def parse_image(self, image_path: Path) -> str:
        """对单张图片进行 OCR，返回 markdown 文本。"""
        ...

    @abstractmethod
    def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
        """解析 PDF，返回 markdown 文本。"""
        ...
```

两个方法均为 `abstractmethod`，不再有默认 `NotImplementedError` 回退。

## 各引擎实现

### siliconflow / ollama

`parse_image` 不变。`parse_pdf` 统一模式：

```python
def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
    image_paths, page_labels = split_pdf(pdf_path, pages)
    try:
        results = []
        for img_path, label in zip(image_paths, page_labels):
            text = self.parse_image(img_path)
            results.append(f"--- 第 {label} 页 ---\n{text}")
        return "\n\n".join(results)
    finally:
        # 清理临时图片
        if image_paths:
            image_paths[0].parent.rmdir()  # 递归情况用 shutil.rmtree
```

### liteparse

`parse_pdf` 保持原生 `liteparse.LiteParse` 实现不变。
`parse_image` 保持图片→临时 PDF→`parse_pdf` 逻辑不变。

## `pdf_utils.py`

新增 `split_pdf` 辅助函数，封装页码范围解析 + PDF 拆图，供各引擎复用：

```python
def split_pdf(
    pdf_path: Path, pages_str: str | None
) -> tuple[list[Path], list[int]]:
    """拆解 PDF：验证页数、解析页码范围、渲染为图片。

    Args:
        pdf_path: PDF 文件路径。
        pages_str: 页码范围字符串（如 "1-3,5"），None 表示全部。

    Returns:
        (图片路径列表, 页码标签列表)，标签为 1-based 页码。

    Raises:
        ValueError: 页码范围无效或越界。
    """
```

现有 `parse_pages`、`pdf_to_images`、`images_to_pdf` 保持不变。

## `single.py`（原 `ocr.py`）

简化后的 `ocr_file`：

```python
def ocr_file(
    input_path: Path,
    engine: OCREngine,
    pages: str | None = None,
) -> str:
    """对 PDF 或图片文件执行 OCR，结果保存为 {input}.md。

    Args:
        input_path: 输入文件路径（PDF 或图片）。
        engine: OCR 引擎实例。
        pages: 页码范围字符串（仅对 PDF 有效）。

    Returns:
        OCR 结果文本。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的文件格式。
    """
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_path}")

    if _is_pdf(input_path):
        merged = engine.parse_pdf(input_path, pages)
    elif _is_image(input_path):
        if pages:
            raise ValueError("图片不支持 --pages 参数")
        merged = engine.parse_image(input_path)
    else:
        raise ValueError(f"不支持的文件格式: {input_path.suffix}")

    output_path = input_path.with_suffix(".md")
    output_path.write_text(merged, encoding="utf-8")
    print(f"已保存: {output_path}")
    return merged
```

不再依赖 `pdf_utils`，不再有 `try/except NotImplementedError` 回退。

## `batch.py`

行为完全不变。唯一改动：`from ocr import ocr_file` → `from single import ocr_file`。

处理逻辑不变：
- 纯图片目录 → 逐张 `engine.parse_image()` → 合并写入 `{目录名}.md`
- 纯 PDF 目录 → 逐文件 `ocr_file()`，各自输出 `.md`
- 混合目录 → 报错

## `main.py`

改动：`from ocr import ocr_file` → `from single import ocr_file`，其余不变。

## 错误处理

| 场景 | 行为 |
|------|------|
| 文件不存在 | 打印错误，exit(1) |
| 不支持的文件格式 | 打印错误，exit(1) |
| `--pages` 范围越界 | `split_pdf` 中抛出 ValueError |
| PDF 页数为 0 | `split_pdf` 中打印错误，exit(1) |
| 引擎 API 错误 | 在 `parse_image` 中抛出 |
| liteparse 处理图片失败 | `parse_image` → 临时 PDF → `parse_pdf` 中抛出 |

## 测试更新

| 文件 | 改动 |
|------|------|
| `tests/test_ocr.py` → `tests/test_single.py` | 重命名，验证 `ocr_file` 分发逻辑（不再测试 PDF 回退） |
| `tests/test_batch.py` | import 路径调整 |
| `tests/test_engines.py` | 新增每个引擎的 `parse_pdf` 单元测试 |
| `tests/test_pdf_utils.py` | 新增 `split_pdf` 测试 |

## 改动文件清单

| 文件 | 改动类型 |
|------|----------|
| `engines/base.py` | 修改 — `parse_pdf` 改为 abstractmethod |
| `engines/siliconflow.py` | 修改 — 新增 `parse_pdf` |
| `engines/ollama.py` | 修改 — 新增 `parse_pdf` |
| `engines/liteparse.py` | 不变 |
| `pdf_utils.py` | 修改 — 新增 `split_pdf` |
| `ocr.py` → `single.py` | 重命名 + 删 PDF 回退逻辑 |
| `batch.py` | 修改 — import 路径 |
| `main.py` | 修改 — import 路径 |
| `tests/test_ocr.py` → `tests/test_single.py` | 重命名 + 更新 |
| `tests/test_batch.py` | 修改 — import 路径 |
| `tests/test_engines.py` | 修改 — 新增 parse_pdf 测试 |
| `tests/test_pdf_utils.py` | 修改 — 新增 split_pdf 测试 |
