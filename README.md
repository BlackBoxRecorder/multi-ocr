# multi-ocr-py

多引擎 OCR 工具包，将 PDF 和图片转换为 Markdown 文档。

- **CLI 工具**：全局安装后一行命令完成 OCR
- **SDK 依赖**：作为 Python 库集成到你的项目中

## 支持的引擎

| 引擎 | 说明 | 类型 | 场景 | 费用 |
|---|---|---|---|---|
| SiliconFlow + DeepSeek-OCR | 云端 OCR，精度高 | API | 图片+PDF | 免费 |
| SiliconFlow + PaddleOCR-VL-1.5 | 云端 OCR，轻量快速 | API | 图片+PDF  | 免费 |
| LiteParse | 本地 PDF 解析，无需联网 | 本地 | PDF  | 免费 |
| Ollama + DeepSeek-OCR | 本地部署 OCR | 本地 | 图片+PDF  | 免费 |


> SiliconFlow 目前提供显示免费的 DeepSeek-OCR、PaddleOCR-VL-1.5 模型调用


> 本地运行 Ollama + DeepSeek-OCR 参考：https://ollama.com/library/deepseek-ocr
> 实测笔记本使用 NVIDIA RTX3060(6GB) 显卡即可流畅使用 Ollama + DeepSeek-OCR


## 安装

### CLI 全局安装

```bash
uv tool install multi-ocr-py
# 或
pip install multi-ocr-py
```

### SDK 依赖安装

```bash
pip install multi-ocr-py
# 或
uv add multi-ocr-py
```

## CLI 使用

```bash
# 单文件 OCR
multi-ocr document.pdf

# 指定引擎和页码范围
multi-ocr document.pdf --model liteparse --pages 1-5

# 批量处理目录，4个并发
multi-ocr ./scans/ --model deepseek -j 4

# 查看帮助
multi-ocr -h
```

**可以使用 `--model` 参数指定模型：**

```bash
# SiliconFlow + DeepSeek-OCR
multi-ocr document.pdf --model deepseek

# SiliconFlow + PaddleOCR-VL-1.5
multi-ocr document.pdf --model paddle

# LiteParse
multi-ocr document.pdf --model liteparse

# Ollama + DeepSeek-OCR
multi-ocr document.pdf --model ollama

```


### 环境变量配置

使用前需要配置以下环境变量：

| 引擎 | 环境变量 | 必需 | 说明 |
|---|---|---|---|
| SiliconFlow | `SILICONFLOW_API_KEY` | ✅ | API Key |
| Ollama | `OLLAMA_BASE_URL` | ❌ | 服务地址，默认 http://127.0.0.1:11434 |

```bash
# 设置 SiliconFlow API Key
export SILICONFLOW_API_KEY="your-api-key"

# 可选：设置 Ollama 服务地址
export OLLAMA_BASE_URL="http://192.168.1.100:11434"
```


## SDK 使用

### 快速开始

```python
from pathlib import Path
from multi_ocr import get_engine, ocr_file, ocr_directory

# 创建引擎（provider 可选: siliconflow / liteparse / ollama）
engine = get_engine(
    provider="siliconflow",
    model="deepseek-ai/DeepSeek-OCR",
    api_key="your-api-key",
)

# 识别单张图片
text = engine.parse_image(Path("scan.jpg"))

# 识别 PDF 单文件，指定页码范围
result = ocr_file(Path("document.pdf"), engine, pages="1-3")

# 批量处理目录（图片或 PDF）
ocr_directory(Path("./scans/"), engine, concurrency=4)
```

### API 参考

#### `get_engine(provider, model, api_key, base_url=None)` → `OCREngine`

创建 OCR 引擎实例。

| 参数 | 类型 | 说明 |
|---|---|---|
| `provider` | `str` | 引擎提供商：`"siliconflow"` / `"liteparse"` / `"ollama"` |
| `model` | `str` | 模型名称，如 `"deepseek-ai/DeepSeek-OCR"` |
| `api_key` | `str` | API 密钥（本地引擎可传空字符串） |
| `base_url` | `str \| None` | 自定义 API 地址（仅 ollama 引擎使用） |

```python
# SiliconFlow + DeepSeek-OCR
engine = get_engine("siliconflow", "deepseek-ai/DeepSeek-OCR", api_key="sk-xxx")

# LiteParse（本地，无需 API Key）
engine = get_engine("liteparse", "", api_key="")

# Ollama + DeepSeek-OCR（本地）
engine = get_engine("ollama", "deepseek-ocr:latest", api_key="", base_url="http://127.0.0.1:11434")
```

#### `engine.parse_image(image_path)` → `str`

对单张图片进行 OCR，返回 Markdown 文本。

| 参数 | 类型 | 说明 |
|---|---|---|
| `image_path` | `Path` | 图片文件路径（支持 .png / .jpg / .jpeg） |

```python
from pathlib import Path
text = engine.parse_image(Path("photo.jpg"))
```

#### `engine.parse_pdf(pdf_path, pages=None, concurrency=1)` → `str`

解析 PDF 文件，返回 Markdown 文本。默认实现会拆页后调用 `parse_image()`，子类可覆盖（如 LiteParse 原生解析）。

| 参数 | 类型 | 说明 |
|---|---|---|
| `pdf_path` | `Path` | PDF 文件路径 |
| `pages` | `str \| None` | 页码范围，如 `"1-3,5"`，`None` 表示全部 |
| `concurrency` | `int` | 并发数，默认 1（串行），>1 时使用线程池 |

```python
from pathlib import Path
# 解析全部页面
result = engine.parse_pdf(Path("doc.pdf"))

# 解析指定页面，4 并发
result = engine.parse_pdf(Path("doc.pdf"), pages="1-5", concurrency=4)
```

#### `ocr_file(input_path, engine, pages=None, concurrency=1)` → `str`

对单个文件执行 OCR 并保存为 `.md` 文件。自动判断图片/PDF。

| 参数 | 类型 | 说明 |
|---|---|---|
| `input_path` | `Path` | 输入文件路径（PDF 或图片） |
| `engine` | `OCREngine` | OCR 引擎实例 |
| `pages` | `str \| None` | 页码范围（仅 PDF 有效） |
| `concurrency` | `int` | 并发数，默认 1 |

```python
from pathlib import Path
from multi_ocr import ocr_file

# 自动输出到同目录下的 .md 文件
result = ocr_file(Path("document.pdf"), engine, pages="1-3")
# → 已保存: document.md
```

#### `ocr_directory(input_dir, engine, concurrency=1)` → `None`

批量处理目录下的图片或 PDF 文件。目录下只能有一种类型（全图片或全 PDF）。

| 参数 | 类型 | 说明 |
|---|---|---|
| `input_dir` | `Path` | 输入目录路径 |
| `engine` | `OCREngine` | OCR 引擎实例 |
| `concurrency` | `int` | 并发数，默认 1 |

```python
from pathlib import Path
from multi_ocr import ocr_directory

# 图片批量 → 输出 scans.md
ocr_directory(Path("./scans/"), engine, concurrency=4)

# PDF 批量 → 每个 PDF 各自输出 .md
ocr_directory(Path("./pdfs/"), engine)
```

### 自定义引擎

继承 `OCREngine` 实现自定义 OCR 引擎：

```python
from pathlib import Path
from multi_ocr import OCREngine

class MyEngine(OCREngine):
    def parse_image(self, image_path: Path) -> str:
        # 你的 OCR 逻辑
        return "recognized text"

    # parse_pdf 可选覆盖，默认实现会拆页后调用 parse_image()
```

## 要求

- Python >= 3.11

## 协议

MIT License
