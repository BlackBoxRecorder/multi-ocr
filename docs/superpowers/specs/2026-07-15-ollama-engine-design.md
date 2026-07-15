# Ollama 本地 DeepSeek-OCR 引擎

## 概述

为 multi-ocr 新增 Ollama 引擎，支持调用本地部署的 DeepSeek-OCR 模型进行 OCR 识别。使用 `ollama` 原生 Python 库，无需 API Key，base_url 可通过环境变量和 CLI 参数配置。

## 核心变更

### 1. 新建 `engines/ollama.py` — OllamaEngine

- 继承 `OCREngine`，实现 `recognize(image_path)`
- 使用 `ollama` 库（`ollama.Client(host=base_url)`）而非 OpenAI SDK
- 构造函数签名：`__init__(self, model: str, api_key: str, base_url: str)`
  - `api_key` 保留以兼容工厂函数签名，实际不使用（传空字符串）
  - `base_url` 默认 `http://127.0.0.1:11434`
- Prompt：`<image>\nFree OCR. Output in markdown format.`
- `recognize()` 通过 `client.chat()` 传入图片二进制数据（`images` 参数）
- 清理输出中的特殊标记（`<|ref|>`、`<|det|>`）

### 2. 修改 `engines/__init__.py` — 注册引擎 + 扩展工厂函数

- 注册 `"ollama" → OllamaEngine`
- `get_engine()` 新增可选参数 `base_url: str | None = None`，转发给引擎构造函数

### 3. 修改 `main.py` — CLI 集成

- `MODEL_MAP` 新增：`"ollama-deepseek-ocr" → ("ollama", "deepseek-ocr:latest", "Ollama + DeepSeek-OCR")`
- Ollama 无 API Key 校验，跳过密钥检查
- 新增 CLI 参数 `--ollama-url`（默认读取环境变量 `OLLAMA_BASE_URL`，都没有则用 `http://127.0.0.1:11434`）
- 将 `base_url` 传入 `get_engine()`

### 4. 修改 `pyproject.toml` — 新增依赖

- 添加 `ollama` 包

## 配置优先级

```
base_url: CLI --ollama-url > 环境变量 OLLAMA_BASE_URL > 默认值 http://127.0.0.1:11434
```

## 使用示例

```bash
# 默认本地地址
python main.py input.png --model ollama-deepseek-ocr

# 指定远程 Ollama 地址
python main.py input.png --model ollama-deepseek-ocr --ollama-url http://192.168.2.4:11434

# 通过环境变量指定
export OLLAMA_BASE_URL=http://192.168.2.4:11434
python main.py input.png --model ollama-deepseek-ocr
```

## 数据流

```
图片文件 → ollama.Client.chat(images=[...]) → 模型返回 markdown 文本 → 清理特殊标记 → 返回结果
```

## 测试要点

- `test_ollama_engine_init`: 验证默认 base_url 和自定义 base_url
- `test_ollama_engine_recognize`: 验证图片识别调用（可 mock ollama Client）
- `test_model_map`: 验证 `ollama-deepseek-ocr` 缩写解析
- `test_base_url_priority`: 验证 CLI > 环境变量 > 默认值
