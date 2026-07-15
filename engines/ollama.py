import re
from pathlib import Path

from ollama import Client

from engines.base import OCREngine


class OllamaEngine(OCREngine):
    """Ollama 本地 OCR 引擎。

    通过 Ollama 调用本地部署的视觉模型进行 OCR 识别。
    无需 API Key，支持自定义 base_url 连接远程 Ollama 实例。
    """

    DEFAULT_BASE_URL = "http://127.0.0.1:11434"

    # 模型名称 -> 提示词映射（按前缀匹配）
    _PROMPT_MAP: dict[str, str] = {
        "deepseek-ocr": "<image>\nFree OCR. Output in markdown format.",
    }

    _FALLBACK_PROMPT = "<image>\nFree OCR. Output in markdown format."

    def __init__(
        self,
        model: str,
        api_key: str = "",
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._model = model
        self._client = Client(host=base_url)

    def _get_prompt(self) -> str:
        """根据模型名称匹配对应的提示词，未匹配则使用默认提示词。"""
        for prefix, prompt in self._PROMPT_MAP.items():
            if prefix in self._model:
                return prompt
        return self._FALLBACK_PROMPT

    def recognize(self, image_path: Path) -> str:
        prompt = self._get_prompt()

        response = self._client.chat(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [str(image_path)],
                }
            ],
        )

        content = response.message.content
        if not content:
            return ""
        # 清理模型可能输出的特殊标记
        content = re.sub(r"<\|/?ref\|>", "", content)
        content = re.sub(r"<\|/?det\|>", "", content)
        return content.strip()
