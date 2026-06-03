"""channel — 消息通道层 (对标 nanobot BaseChannel)"""

import requests


class Message:
    """一条消息"""

    def __init__(self, role: str, content: str, name: str | None = None):
        self.role = role
        self.content = content
        self.name = name


class BaseChannel:
    """通道接口: recv / send / send_tool_result"""

    def recv(self):
        raise NotImplementedError

    def send(self, msg: Message):
        raise NotImplementedError

    def send_tool_result(self, tool_call_id: str, content: str):
        raise NotImplementedError


class StdinChannel(BaseChannel):
    """终端: input() 读入, print() 输出"""

    def recv(self):
        print("我是机器人，请输入消息：")
        s = input()
        return Message(role = 'user',content = s)

    def send(self, msg: Message):
        print(f"慢慢机器人回复: {msg.content}")

    def send_tool_result(self, tool_call_id: str, content: str):
        print(f"工具调用结果: {content}")
        
        
class TelegramChannel(BaseChannel):
    """Telegram 机器人通道"""

    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0  # 记录已处理的最新 update_id

    def recv(self) -> Message:
        """轮询 Telegram，阻塞等待新消息"""
        while True:
            resp = requests.get(
                f"{self.base_url}/getUpdates",
                params={"offset": self.offset, "timeout": 30},
            )
            data = resp.json()
            if not data.get("ok"):
                continue
            for update in data.get("result", []):
                self.offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                if text:
                    # 记住 chat_id，后面回复要用
                    self._chat_id = msg["chat"]["id"]
                    return Message(role="user", content=text)

    def send(self, msg: Message):
        """发文字消息到 Telegram"""
        requests.post(
            f"{self.base_url}/sendMessage",
            json={"chat_id": self._chat_id, "text": msg.content},
        )

    def send_voice(self, audio_path: str):
        """发语音消息到 Telegram"""
        with open(audio_path, "rb") as f:
            requests.post(
                f"{self.base_url}/sendVoice",
                data={"chat_id": self._chat_id},
                files={"voice": (audio_path, f, "audio/ogg")},
            )

