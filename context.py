"""context — 上下文管理 (对标 nanobot ContextBuffer)"""

class ContextBuffer:
    """滑动窗口上下文: system_prompt + messages[], FIFO 截断"""

    def __init__(self, system_prompt: str = "", max_entries: int = 50, memory = None, max_tokens = 8000):
        self.system_prompt = system_prompt
        self.max_entries = max_entries
        self.max_tokens = max_tokens
        self.messages = []
        self.memory = memory # 长期记忆，独立于消息上下文之外，可以设计成一个工具供agent调用
        self.archived_summary = "" # 压缩后得摘要
    

    def add_message(self, role,content,name=None,tool_call_id=None):
        "添加消息到上下文中，支持user/assistant/tool角色"
        msg = {"role":role,"content":content}
        if name is not None:
            msg["name"] = name
        if tool_call_id is not None:
            msg["tool_call_id"] = tool_call_id
        self.messages.append(msg)
        if len(self.messages) > self.max_entries:
            self.messages.pop(0) # 超过长度限制，丢弃最早消息
            
    def estimate_tokens(self):
        """估算当前上下文token数 （中文约 1.5 char/token，英文约 4 char/token，取 2）"""
        total = 0
        for msg in self.messages:
            content = msg.get("content","")
            if content:
                total += len(content) // 2
        if self.system_prompt:
            total += len(self.system_prompt) // 2
        if self.archived_summary:
            total += len(self.archived_summary) // 2
        return total
        

    def get_prompt(self):
        """组装完整的 messages 给 LLM"""
        # system prompt 内容
        system_parts = []
        if self.system_prompt:
            system_parts.append(self.system_prompt)
        # 注入 MEMORY.md 内容
        if self.memory:
            mem_ctx = self.memory.get_memory_context()
            if mem_ctx:
                system_parts.append(f"# 记忆\n\n{mem_ctx}")
        # 注入压缩摘要
        if self.archived_summary:
            system_parts.append(f"[历史摘要]\n\n{self.archived_summary}")

        system_content = "\n\n".join(system_parts)
        result = []
        if system_content:
            result.append({"role": "system", "content": system_content})
        result.extend(self.messages)
        return result

    def consolidate(self, agent):
          """上下文超长时，把前半段消息用 LLM 总结成摘要"""
          if len(self.messages) < 4:
              return  # 消息太少，没必要压缩

          # 取前 60% 的消息去总结
          split = len(self.messages) * 3 // 5
          old_messages = self.messages[:split]
          self.messages = self.messages[split:]

          # 把旧消息格式化成文本，让 LLM 总结
          summary_prompt = []
          if self.system_prompt:
              summary_prompt.append({"role": "system", "content":
  "你是一个对话摘要助手。请把以下对话总结成一段简洁的中文摘要，保留关键信息。"})
          summary_prompt.extend(old_messages)
          summary_prompt.append({"role": "user", "content":
  "请总结以上对话的关键内容。"})

          # 用独立的 agent 调用做总结（不带工具，纯文本）
          old_tools = agent.tools
          agent.tools = None  # 临时去掉工具，避免总结时调工具
          try:
              summary = agent.chat(summary_prompt)
          except Exception:
              summary = "(摘要生成失败)"
          finally:
              agent.tools = old_tools  # 恢复工具

          # 拼接到已有摘要后面
          if self.archived_summary:
              self.archived_summary += "\n\n" + summary
          else:
              self.archived_summary = summary

          # 写入 history.jsonl
          if self.memory:
              self.memory.append_history(summary)

    def clear(self):
        "清空上下文"
        self.messages = []
        self.archived_summary = ""
