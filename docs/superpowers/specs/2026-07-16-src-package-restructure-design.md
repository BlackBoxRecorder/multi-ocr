# src 目录重构：CLI 全局安装 + SDK 依赖包

## 概述

将项目代码统一移入 `src/multi_ocr/` 目录，配置 `pyproject.toml` 使其支持：
- `uv tool install .` 全局安装为 `multi-ocr` CLI 工具
- `pip install multi-ocr` 作为 SDK 依赖包使用

## 文件结构

```
multi-ocr/
├── src/
│   └── multi_ocr/
│       ├── __init__.py          # SDK 公开接口
│       ├── cli.py               # CLI 入口（原 main.py）
│       ├── single.py            # 单文件 OCR
│       ├── batch.py             # 批量 OCR
│       ├── pdf_utils.py         # PDF 工具函数
│       └── engines/
│           ├── __init__.py      # 引擎注册表 + get_engine() 工厂
│           ├── base.py          # OCREngine 抽象基类
│           ├── dashscope.py     # DashScope 引擎
│           ├── liteparse.py     # LiteParse 引擎（可选依赖）
│           ├── ollama.py        # Ollama 引擎
│           └── siliconflow.py   # SiliconFlow 引擎
├── tests/                       # 保持根目录
│   ├── conftest.py
│   ├── test_batch.py
│   ├── test_engines.py
│   ├── test_pdf_utils.py
│   └── test_single.py
├── pyproject.toml
└── .gitignore
```

## pyproject.toml 变更

### 新增构建系统配置

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 新增 CLI 入口点

```toml
[project.scripts]
multi-ocr = "multi_ocr.cli:main"
```

### pytest 配置更新

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```

## 导入路径变更

所有包内导入从相对路径改为包绝对路径：

| 原导入 | 新导入 |
|---|---|
| `from engines import get_engine` | `from multi_ocr.engines import get_engine` |
| `from engines.base import OCREngine` | `from multi_ocr.engines.base import OCREngine` |
| `from single import ocr_file` | `from multi_ocr.single import ocr_file` |
| `from batch import ocr_directory` | `from multi_ocr.batch import ocr_directory` |
| `from pdf_utils import parse_pages` | `from multi_ocr.pdf_utils import parse_pages` |

## SDK 公开接口

`src/multi_ocr/__init__.py` 对外暴露精简接口：

- `get_engine()` — 引擎工厂函数
- `OCREngine` — 抽象基类（支持第三方开发自定义引擎）
- `ocr_file()` — 单文件 OCR
- `ocr_directory()` — 批量 OCR

`pdf_utils` 内部函数（`parse_pages`、`pdf_to_images` 等）不暴露到顶层。

## 文件移动清单

1. `main.py` → `src/multi_ocr/cli.py`
2. `single.py` → `src/multi_ocr/single.py`
3. `batch.py` → `src/multi_ocr/batch.py`
4. `pdf_utils.py` → `src/multi_ocr/pdf_utils.py`
5. `engines/` → `src/multi_ocr/engines/`

## 使用方式

### CLI 全局安装

```bash
uv tool install .
multi-ocr mydoc.pdf --model silicon-deepseek-ocr
```

### SDK 依赖安装

```python
from multi_ocr import get_engine, ocr_file, OCREngine

engine = get_engine("siliconflow", "deepseek-ai/DeepSeek-OCR", api_key="...")
result = ocr_file(Path("mydoc.pdf"), engine)
```

## 测试策略

- 测试文件保持根目录 `tests/`，更新 pytest 的 `pythonpath` 为 `["src"]`
- 测试中导入路径改为 `from multi_ocr.xxx import ...`
- 运行 `pytest` 验证所有功能和导入正确
- 验证 `uv tool install .` 后 CLI 可正常执行
