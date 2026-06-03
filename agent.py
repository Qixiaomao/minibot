"""agent — LLM 调用 + function calling 循环 (对标 nanobot Agent)"""

import requests
import json
import time

# 核心: while 循环处理 tool_call
#   LLM → tool_call → 执行工具 → 结果塞回 messages → 再调 LLM
#   LLM → 文本 → 结束




class Agent:
    # def __init__(self, api_key, base_url, model, tool_schemas, execute_tool, proxy=None):
    #     ...
    def __init__(self, api_key, base_url, model="mimo-v2.5-pro",tools = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.tools = tools # tool registry, 提供工具定义和执行接口
        
    def _build_tools_list(self):
        """组装发给LLM的tool参数:function tools + MiMo 原生 web_search"""
        tools_list = []
        if self.tools:
            tools_list.extend(self.tools.get_schemas())
        # 添加 MiMo 原生工具
        return tools_list if tools_list else None
    
    def _request_with_retry(self, body, max_retries = 3):
        """ 带指数退避的请求重试机制"""
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                  json=body,
                  timeout=30,
                )
                resp.raise_for_status()
                return resp.json()
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
               if attempt < max_retries - 1:  # 还有重试机会
                  wait = 2 ** attempt # 指数退避等待时间
                  print(f"请求发生异常: {e}，{wait}秒后重试...（第{attempt + 1}次）")
                  time.sleep(wait) # 等待1秒后重试
               else:
                   raise
        
    
    
    
    def chat(self, messages):
        """发送 messages 给 LLM，自动处理 tool calling循环，返回最终文本回复。"""
        max_rounds = 5  # 最多 5 轮 tool calling，防止死循环

        for _ in range(max_rounds):
            body = {
                  "model": self.model,
                  "messages": messages,
              }
            tools_list = self._build_tools_list()
            if tools_list:
                  body["tools"] = tools_list
            
            result = self._request_with_retry(body) 
            choice = result["choices"][0]
            msg = choice["message"]

            # LLM 要调工具
            if choice.get("finish_reason") == "tool_calls" and msg.get("tool_calls"):
                  # 1. 把 assistant 的 tool_calls 消息追加进去
                  messages.append({
                      "role": "assistant",
                      "content": msg.get("content"),
                      "tool_calls": msg["tool_calls"],
                  })

                  # 2. 逐个执行工具，结果塞回 messages
                  for tc in msg["tool_calls"]:
                      name = tc["function"]["name"]
                      args = tc["function"]["arguments"]
                      if self.tools:
                          result_text = self.tools.execute(name, args)
                      else:
                          result_text = f"Error: no tool registry, cannot execute '{name}'"
                      messages.append({
                          "role": "tool",
                          "tool_call_id": tc["id"],
                          "name": name,
                          "content": result_text,
                      })
                  continue  # 回到循环开头，把 tool 结果再发给 LLM

            # LLM 给出最终文本回复
            return msg.get("content", "")

        return "Error: tool calling 轮次超限"

