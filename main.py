"""main — 主循环入口"""

import os
from dotenv import load_dotenv
from channel import TelegramChannel, Message
from agent import Agent
from context import ContextBuffer
from tools import ToolRegistry
from builtin_tools import register_builtin_tools
from memory import MemoryStore


def main():
    load_dotenv()

    channel = TelegramChannel(token=os.getenv("TELEGRAM_TOKEN"))

    # 工具注册
    registry = ToolRegistry()
    register_builtin_tools(registry, workspace="./workspace")  # 注册一些内置工具，如计算器、天气查询等

    # 记忆
    memory = MemoryStore(workspace = "./workspace")

    # Agent (MiMo Pro + tool)
    agent = Agent(
        api_key = os.getenv("MIMO_API_KEY"),
        base_url = os.getenv("MIMO_BASE_URL"),
        model = os.getenv("MIMO_MODEL"),
        tools = registry,
    )
    
    # 上下文 （注入memory)
    ctx  = ContextBuffer(
        system_prompt = "你是一个可爱的三花猫助手，调皮，喜欢吃鱼，喜欢和人类朋友聊天。",
        max_entries = 50,
        memory=memory,
        max_tokens = 8000,
    )
    
    # 语音模块 暂时不用
    # tts = TTS(
    #     api_key=os.getenv("MIMO_API_KEY"),
    #     base_url=os.getenv("MIMO_BASE_URL"),
    # )
    
    
    while True:
       msg = channel.recv() # 接收消息，阻塞直到收到
       ctx.add_message("user",msg.content)
       
       # 上下文超长时自动压缩
       if ctx.estimate_tokens() > ctx.max_tokens:
           ctx.consolidate(agent)
           
       reply = agent.chat(ctx.get_prompt()) # 将上下文传给agent，得到回复
       ctx.add_message("assistant",reply) # 将回复添加到上下文中
       channel.send(Message(role="assistant", content=reply)) # 将回复发回去


if __name__ == "__main__":
    main()
