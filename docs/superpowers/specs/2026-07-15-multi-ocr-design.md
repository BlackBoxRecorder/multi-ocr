# Multi-OCR 设计文档

## 概述

一个 Python CLI 工具，调用 SiliconFlow API 的 OCR 模型（DeepSeek-OCR / PaddleOCR-VL-1.5），将 PDF 和图片转换为文字。采用策略模式设计引擎层，未来可方便扩展其他 OCR 提供商。

## 模块结构

```
multi-ocr/
├── main.py              # CLI 入口，argparse 参数解析
├── ocr.py                # OCR 编排：PDF 拆页 → 逐页识别 → 合并输出
├── pdf_utils.py          # PDF → 图片转换（pymupdf）
├── engines/
│   ├── __init__.py       # 引擎注册表 + get_engine() 工厂函数
│   ├── base.py           # OCREngine 抽象基类
│   └── siliconflow.py    # SiliconFlow 引擎实现（OpenAI SDK）
└── pyproject.toml
```

## CLI 接口

### 用法

```bash
# 基本用法（默认 siliconflow + deepseek-ai/DeepSeek-OCR）
python main.py input.pdf

# 指定模型
python main.py input.pdf --model PaddlePaddle/PaddleOCR-VL-1.5

# 指定页码范围
python main.py input.pdf --pages 1-3,5

# 输出到终端
python main.py input.pdf --stdout

# 覆盖 API Key
python main.py input.pdf --api-key sk-xxx

# 图片输入
python main.py photo.png
```

### 参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `input` | 是 | — | PDF 或图片文件路径（支持 .pdf/.png/.jpg/.jpeg） |
| `--provider` | 否 | `siliconflow` | OCR 服务提供商 |
| `--model` | 否 | `deepseek-ai/DeepSeek-OCR` | 模型名称 |
| `--pages` | 否 | 全部 | 页码范围，如 `1-3,5` |
| `--api-key` | 否 | `$SILICONFLOW_API_KEY` | API Key，优先级：命令行 > 环境变量 |
| `--stdout` | 否 | `False` | 输出到终端而非保存文件 |

### 输出

- 默认：保存为 `{input文件名}.txt`，与输入文件同目录
- `--stdout`：直接打印到终端，不保存文件
- 多页 PDF 每页前加 `--- 第 N 页 ---` 分隔

## 引擎抽象层

### OCREngine 基类 (`engines/base.py`)

```python
class OCREngine(ABC):
    @abstractmethod
    def recognize(self, image_path: Path) -> str:
        """对单张图片进行 OCR，返回识别文本。"""
```

极简接口 — 只有一个方法。新引擎只需实现此接口。

### 注册表 (`engines/__init__.py`)

```python
_registry: dict[str, type[OCREngine]] = {}

def get_engine(provider: str, model: str, api_key: str) -> OCREngine
```

工厂函数按 `provider` 名查找注册的引擎类并实例化。添加新提供商只需：
1. 新建 `engines/<provider>.py`，实现 `OCREngine`
2. 在 `_registry` 中注册

### SiliconFlow 引擎 (`engines/siliconflow.py`)

- 使用 `openai` SDK，`base_url="https://api.siliconflow.cn/v1"`
- `recognize()` 流程：
  1. 读取图片 → base64 编码
  2. 构造 vision message：
     ```json
     {
       "role": "user",
       "content": [
         {"type": "text", "text": "请识别图片中的文字，只输出识别结果，不要额外解释。"},
         {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
       ]
     }
     ```
  3. 调用 `client.chat.completions.create(model=..., messages=...)`
  4. 返回 `response.choices[0].message.content`

## PDF 处理 (`pdf_utils.py`)

- 使用 `pymupdf`（fitz）渲染每页为 PNG
- 输出到系统临时目录，OCR 完成后自动清理
- `parse_pages(pages_str, total_pages)` — 解析 `--pages` 参数，1-based 输入转为 0-based index
- 页码格式：逗号分隔 + 范围，如 `1,3-5,8`

## OCR 编排 (`ocr.py`)

```
ocr_file(input_path, engine, pages=None, stdout=False) -> str
```

流程：
1. 检查文件存在性，判断类型（PDF 还是图片）
2. PDF → `pdf_utils` 拆页得图片列表；图片 → 单元素列表
3. 按 `pages` 过滤（仅 PDF）
4. 逐页调用 `engine.recognize(image_path)`
5. 合并结果（多页加分隔符）
6. 输出：`--stdout` → print；否则写入 `{stem}.txt`

## 错误处理

| 场景 | 行为 |
|------|------|
| 文件不存在 | 打印错误，exit(1) |
| 不支持的文件格式 | 打印错误，exit(1) |
| API Key 未设置 | 打印"请设置 SILICONFLOW_API_KEY 环境变量或使用 --api-key"，exit(1) |
| API 网络/鉴权/限流错误 | 打印错误详情，exit(1) |
| PDF 页数为 0 | 打印"PDF 无内容"，exit(1) |
| 临时目录创建失败 | 打印错误，exit(1) |
| `--pages` 范围越界 | 打印错误，exit(1) |

## 依赖

通过 `uv add` 管理：

| 包 | 用途 |
|---|---|
| `openai` | SiliconFlow OpenAI 兼容 API |
| `pymupdf` | PDF 渲染为图片 |

仅标准库 + 两个第三方包，无其他依赖。

## 扩展点

未来扩展方向（不在此次实现范围）：
- 新 OCR 提供商（如阿里云、百度云 OCR）：新建 `engines/<provider>.py` + 注册
- 多 provider 自动 fallback
- 输出格式扩展（JSON、Markdown）
- 批量目录处理
