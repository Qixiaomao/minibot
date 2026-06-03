"""test_tts — 测试 MiMo TTS"""

from tts import TTS

# 用你的 API key
tts = TTS(api_key="你的api_key")

# 基础用法：文字 → 音频文件
tts.synthesize(
    text="你好，我是慢慢，一只会说话的猫猫机器人。",
    style="温柔可爱的语气",
    output="hello.mp3",
)
print("音频已生成: hello.mp3")

# 带方言
tts.synthesize(
    text="哎呀妈呀，这也太好了吧！",
    style="东北话，热情豪爽",
    output="dongbei.mp3",
)
print("音频已生成: dongbei.mp3")
