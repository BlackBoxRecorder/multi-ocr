import base64
import re
from pathlib import Path

from openai import OpenAI

from multi_ocr.engines.base import OCREngine


class DashScopeEngine(OCREngine):
    """DashScope (阿里云百炼) OCR 引擎，兼容 OpenAI SDK。

    支持 Qwen-VL-OCR 模型，通过 OpenAI 兼容接口调用。
    参考文档：https://help.aliyun.com/zh/model-studio/qwen-ocr

    默认为通用 OCR 场景，如需使用内置任务（高精识别、表格解析、信息抽取等），
    可参照文档在 prompt 中传入对应指令。
    """

    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 模型名称 -> 提示词映射（按前缀匹配）
    _PROMPT_MAP: dict[str, str] = {
        "qwen-vl-ocr": "OCR this image and output in markdown format.",
    }

    _FALLBACK_PROMPT = "OCR this image and output in markdown format."

    def __init__(self, model: str, api_key: str, base_url: str | None = None) -> None:
        self._model = model
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url or self.BASE_URL,
            timeout=120.0,
        )

    def _get_prompt(self) -> str:
        """根据模型名称匹配对应的提示词，未匹配则使用默认提示词。"""
        for prefix, prompt in self._PROMPT_MAP.items():
            if prefix in self._model:
                return prompt
        return self._FALLBACK_PROMPT

    def parse_image(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # 根据扩展名确定 MIME 类型
        suffix = image_path.suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
        mime_type = mime_map.get(suffix, "image/png")

        data_url = f"data:{mime_type};base64,{image_data}"

        prompt = self._get_prompt()

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        content = response.choices[0].message.content
        if not content:
            return ""
        # 清理模型可能输出的特殊标记
        content = re.sub(r"<\|/?ref\|>", "", content)
        content = re.sub(r"<\|/?det\|>", "", content)
        # 剥离 markdown 代码块包裹（如 ```markdown ... ```）
        content = re.sub(r"^```(?:markdown)?\s*\n", "", content, count=1)
        content = re.sub(r"\n```\s*$", "", content)
        return content.strip()
