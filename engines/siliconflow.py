import base64
from pathlib import Path

from openai import OpenAI

from engines.base import OCREngine


class SiliconFlowEngine(OCREngine):
    """SiliconFlow API OCR 引擎，兼容 OpenAI SDK。"""

    BASE_URL = "https://api.siliconflow.cn/v1"

    def __init__(self, model: str, api_key: str) -> None:
        self._model = model
        self._client = OpenAI(api_key=api_key, base_url=self.BASE_URL)

    def recognize(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # 根据扩展名确定 MIME 类型
        suffix = image_path.suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
        mime_type = mime_map.get(suffix, "image/png")

        data_url = f"data:{mime_type};base64,{image_data}"

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请识别图片中的文字，只输出识别结果，不要额外解释。",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
        )

        content = response.choices[0].message.content
        return content if content else ""
