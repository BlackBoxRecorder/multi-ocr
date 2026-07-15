# --model 缩写映射设计

## 概述

为 `--model` 参数引入 provider+model 缩写映射，用一个参数替代原有的 `--provider` + `--model` 组合，简化 CLI 使用。移除 `--provider` 参数，`--model` 仅接受预定义的缩写值。

## 动机

当前用户需要分别指定 `--provider` 和 `--model`，且模型名很长：

```bash
python main.py input.pdf --provider siliconflow --model deepseek-ai/DeepSeek-OCR
python main.py input.pdf --provider dashscope --model qwen3.5-ocr
```

改为缩写后：

```bash
python main.py input.pdf --model silicon-deepseek-ocr
python main.py input.pdf --model dashscope-qwen-ocr
```

## MODEL_MAP 定义

在 `main.py` 中定义映射表，每个缩写对应 `(provider, model_name, description)`：

```python
MODEL_MAP: dict[str, tuple[str, str, str]] = {
    "silicon-deepseek-ocr":  ("siliconflow", "deepseek-ai/DeepSeek-OCR",       "SiliconFlow + DeepSeek-OCR"),
    "silicon-paddle-ocr":    ("siliconflow", "PaddlePaddle/PaddleOCR-VL-1.5",  "SiliconFlow + PaddleOCR-VL-1.5"),
    "dashscope-qwen-ocr":    ("dashscope",   "qwen3.5-ocr",                    "DashScope + Qwen-OCR"),
    "dashscope-qwen-vl-ocr": ("dashscope",   "qwen-vl-ocr",                    "DashScope + Qwen-VL-OCR"),
}
```

默认模型缩写：

```python
DEFAULT_MODEL = "silicon-deepseek-ocr"
```

## CLI 参数变更

### 移除

- `--provider` 参数

### 修改

- `--model`：仅接受 `MODEL_MAP` 中的 key，默认值 `silicon-deepseek-ocr`
- `--api-key` 的 help 文本更新，说明环境变量由 `--model` 自动决定

### 不变

- `--pages`、`--stdout` 行为不变
- 输入文件参数不变

## `-h` 输出设计

`--model` 的 help 文本动态列出所有可用缩写及对应描述：

```
--model MODEL       模型缩写（默认: silicon-deepseek-ocr）
                    可用模型:
                      silicon-deepseek-ocr   → SiliconFlow + DeepSeek-OCR
                      silicon-paddle-ocr     → SiliconFlow + PaddleOCR-VL-1.5
                      dashscope-qwen-ocr     → DashScope + Qwen-OCR
                      dashscope-qwen-vl-ocr  → DashScope + Qwen-VL-OCR
```

`--api-key` 的 help 提示用户根据模型配置对应环境变量：

```
--api-key API_KEY   API Key（根据 --model 自动读取对应环境变量：
                      siliconflow 模型 → SILICONFLOW_API_KEY
                      dashscope 模型   → DASHSCOPE_API_KEY）
```

## 主流程变更（`main.py`）

```
用户传入 --model silicon-deepseek-ocr
        │
        ▼
查 MODEL_MAP → provider="siliconflow", model_name="deepseek-ai/DeepSeek-OCR"
        │
        ▼
查 _PROVIDER_CONFIG → env_var="SILICONFLOW_API_KEY"
        │
        ▼
get_engine(provider, model_name, api_key) → OCR 引擎实例
        │
        ▼
ocr_file(...) → 执行 OCR
```

- `_PROVIDER_CONFIG` 简化为仅存 provider → env_var 映射，不再包含默认模型
- 如果用户传入的 `--model` 值不在 `MODEL_MAP` 中，报错并列出有效缩写

## 引擎层不变

`engines/__init__.py`、`engines/base.py`、各引擎类无需任何改动。缩写映射是 CLI 层概念，引擎层只感知 provider 名和完整模型名。

## 测试要点

| 场景 | 预期 |
|------|------|
| `--model silicon-deepseek-ocr` | 正确推导 provider=SiliconFlow，使用 DeepSeek-OCR |
| `--model dashscope-qwen-ocr` | 正确推导 provider=DashScope，使用 qwen3.5-ocr |
| `--model invalid-model` | 报错退出，列出所有可用缩写 |
| 不传 `--model` | 使用默认值 `silicon-deepseek-ocr` |
| 未设置对应环境变量 | 提示设置对应环境变量（如 SILICONFLOW_API_KEY） |
| `-h` 输出 | 显示所有可用模型缩写及对应环境变量说明 |
