# LiteParse 引擎集成设计文档

## 概述

新增 LiteParse 作为本地 PDF 解析引擎。LiteParse 是一个基于 Rust 的开源文档解析库，Python 包 `liteparse` 可直接调用，无需 API Key、无需联网，能直接解析 PDF 并输出 markdown。

与现有云端引擎（如 SiliconFlow）不同，LiteParse **仅处理 PDF**，不处理图片。同时，本次统一所有引擎的输出格式为 markdown，保存扩展名改为 `.md`。

## 引擎接口扩展

### OCREngine 基类 (`engines/base.py`)

新增 `parse_pdf()` 方法，默认抛 `NotImplementedError`，现有引擎无需修改：

```python
class OCREngine(ABC):
    @abstractmethod
    def recognize(self, image_path: Path) -> str:
        """对单张图片进行 OCR，返回 markdown 文本。"""
        ...

    def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
        """直接解析 PDF，返回 markdown 文本。
        默认不支持，子类可按需覆写。
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} 不支持直接解析 PDF"
        )
```

### LiteParse 引擎 (`engines/liteparse.py`)

新文件，实现 `OCREngine`：

- `__init__(model="", api_key="")`：接受参数保持工厂函数签名兼容，但不使用
- `recognize(image_path)`：抛 `NotImplementedError`（仅支持 PDF）
- `parse_pdf(pdf_path, pages=None)`：调用 `liteparse.LiteParse` 直接解析，透传 `pages` 为 `target_pages`，输出 markdown

```python
from liteparse import LiteParse as LiteParseLib

class LiteParseEngine(OCREngine):
    def __init__(self, model: str = "", api_key: str = "") -> None:
        self._parser = LiteParseLib(output_format="markdown")

    def parse_pdf(self, pdf_path: Path, pages: str | None = None) -> str:
        kwargs = {}
        if pages:
            kwargs["target_pages"] = pages
        self._parser = LiteParseLib(output_format="markdown", **kwargs)
        result = self._parser.parse(str(pdf_path))
        return result.text
```

其余 LiteParse 配置项（`ocr_enabled`、`ocr_language`、`dpi` 等）全部使用默认值。

## 注册表 (`engines/__init__.py`)

```python
_registry: dict[str, type[OCREngine]] = {
    "siliconflow": SiliconFlowEngine,
    "liteparse": LiteParseEngine,
}
```

## OCR 编排层 (`ocr.py`)

### PDF 处理分支

`ocr_file()` 中增加 PDF 处理分支：引擎支持 `parse_pdf()` 时跳过 PDF→图片 步骤，直接解析。

```
ocr_file(input_path, engine, pages)
  ├── PDF + parse_pdf 支持 → engine.parse_pdf() 直接解析
  ├── PDF + 不支持       → 走原流程（PDF→图片→逐页 OCR）
  └── 图片文件           → 走原流程（逐张 OCR）
```

### 输出扩展名变更

所有引擎输出文件扩展名从 `.txt` 改为 `.md`。

## CLI (`main.py`)

### 模型映射

```python
MODEL_MAP = {
    ...
    "liteparse": ("liteparse", "", "LiteParse (本地 PDF 解析)"),
}
```

### API Key 跳过

当 `provider == "liteparse"` 时，跳过 API Key 校验（LiteParse 不需要 API Key）。

LiteParse 也不在 `_PROVIDER_ENV` 中注册环境变量。

## 依赖 (`pyproject.toml`)

```toml
dependencies = [
    "openai>=2.45.0",
    "pymupdf>=1.28.0",
    "tqdm>=4.67.0",
    "liteparse",
]
```

## 使用方式

```bash
# LiteParse 解析 PDF
python main.py input.pdf --model liteparse

# 指定页码范围
python main.py input.pdf --model liteparse --pages 1-3,5
```

## 测试

### `tests/test_engines.py`

新增 `test_liteparse_provider`：验证 `get_engine(provider="liteparse", ...)` 返回 `LiteParseEngine` 实例。

### `tests/test_ocr.py`

- 更新输出扩展名为 `.md`
- 新增 `test_ocr_pdf_with_liteparse`：验证 PDF 直接走 `parse_pdf` 分支

## 改动文件清单

| 文件 | 改动类型 |
|------|----------|
| `engines/base.py` | 修改 — 新增 `parse_pdf()` 方法 |
| `engines/liteparse.py` | **新文件** |
| `engines/__init__.py` | 修改 — 注册 LiteParseEngine |
| `ocr.py` | 修改 — PDF 分支判断 + `.md` 扩展名 |
| `main.py` | 修改 — MODEL_MAP + 跳过 API Key |
| `pyproject.toml` | 修改 — 加 `liteparse` 依赖 |
| `tests/test_engines.py` | 修改 — 新增 LiteParse 工厂测试 |
| `tests/test_ocr.py` | 修改 — 更新扩展名 + 新增测试用例 |
