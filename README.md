# multi-ocr

多引擎 OCR 工具包，将 PDF 和图片转换为 Markdown 文档。

- **CLI 工具**：全局安装后一行命令完成 OCR
- **SDK 依赖**：作为 Python 库集成到你的项目中

## 支持的引擎

| 引擎 | 说明 | 类型 |
|---|---|---|
| SiliconFlow + DeepSeek-OCR | 云端 OCR，精度高 | API |
| SiliconFlow + PaddleOCR-VL-1.5 | 云端 OCR，轻量快速 | API |
| DashScope + Qwen-VL-OCR | 阿里云百炼 | API |
| LiteParse | 本地 PDF 解析，无需联网 | 本地 |
| Ollama + DeepSeek-OCR | 本地部署 OCR | 本地 |

## 安装

### CLI 全局安装

```bash
uv tool install multi-ocr
# 或
pip install multi-ocr
```

### SDK 依赖安装

```bash
pip install multi-ocr
# 或
uv add multi-ocr
```

## CLI 使用

```bash
# 单文件 OCR
multi-ocr document.pdf

# 指定引擎和页码范围
multi-ocr document.pdf --model dashscope-qwen-vl-ocr --pages 1-5

# 批量处理目录
multi-ocr ./scans/ --model silicon-deepseek-ocr -j 4

# 查看帮助
multi-ocr --help
```

### 环境变量

| 引擎 | 环境变量 |
|---|---|
| SiliconFlow | `SILICONFLOW_API_KEY` |
| DashScope | `DASHSCOPE_API_KEY` |
| Ollama | `OLLAMA_BASE_URL`（可选，默认 http://127.0.0.1:11434）|

也可通过 `--api-key` 参数直接传入。

## SDK 使用

```python
from pathlib import Path
from multi_ocr import get_engine, ocr_file, OCREngine

# 创建引擎
engine = get_engine(
    provider="siliconflow",
    model="deepseek-ai/DeepSeek-OCR",
    api_key="your-api-key",
)

# 识别图片
text = engine.parse_image(Path("scan.jpg"))

# 识别 PDF
result = ocr_file(Path("document.pdf"), engine, pages="1-3")

# 批量处理目录
from multi_ocr import ocr_directory
ocr_directory(Path("./scans/"), engine, concurrency=4)
```

### 自定义引擎

```python
from multi_ocr import OCREngine

class MyEngine(OCREngine):
    def parse_image(self, image_path: Path) -> str:
        # 你的 OCR 逻辑
        return "recognized text"
```

## 要求

- Python >= 3.11

## 协议

MIT License
