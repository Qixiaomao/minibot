"""tts — Xiaomi MiMo-V2.5-TTS 语音合成"""

import requests
import base64


class TTS:
    """MiMo TTS: text → 音频文件"""

    def __init__(self, api_key: str, base_url: str = "https://api.xiaomimimo.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def synthesize(self, text: str, style: str = "", voice: str = "冰糖", output: str = "output.wav") -> str:
        """
        调用 MiMo TTS API，生成音频文件。

        Args:
            text:    要合成的文字
            style:   风格描述（可选），如 "开心的语气"、"东北话"
            voice:   音色，如 "冰糖"、"苏打"、"Mia"
            output:  输出文件路径

        Returns:
            输出文件路径
        """
        # MiMo TTS 的格式：
        #   user message = 风格指令（告诉模型用什么语气）
        #   assistant message = 要朗读的文字
        messages = [
            {"role": "user", "content": style or "请用自然的语气朗读以下内容"},
            {"role": "assistant", "content": text},
        ]

        body = {
            "model": "mimo-v2.5-tts",
            "messages": messages,
            "audio": {
                "format": "wav",
                "voice": voice,
            },
        }

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        result = resp.json()

        audio_b64 = result["choices"][0]["message"]["audio"]["data"]
        audio_bytes = base64.b64decode(audio_b64)

        with open(output, "wb") as f:
            f.write(audio_bytes)

        return output
