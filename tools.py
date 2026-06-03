"""tools — 工具注册与执行 (对标 nanobot Skill 系统)"""
import json

class ToolRegistry:
    """注册: (函数, OpenAI function schema) → 按名执行"""

    def __init__(self):
        self._tools = {} # name → (func, description, parameters)
    
    def register(self, name, func, description="", parameters=None):
        """_summary_ 注册一个工具函数，提供给LLM调用

         parameters 是 JSON Schema，如:
          {
              "type": "object",
              "properties": {
                  "expression": {"type": "string", "description": "数学表达式"}
              },
              "required": ["expression"]
          }        
          """
        self._tools[name] = {
              "func":func,
              "description":description,
              "parameters":parameters or {"type":"object","properties":{}},
          }

    def get_schemas(self):
        "返回 openai function-calling 格式的工具定义列表"
        schemas = []
        for name, tool in self._tools.items():
            schemas.append({
                "type":"function",
                "function":{
                    "name":name,
                    "description":tool["description"],
                    "parameters":tool["parameters"],
                },
            })
        return schemas

    def execute(self, name: str, arguments: dict):
        "执行名称工具函数，返回字符串结果。出错返回错误信息"
        tool = self._tools.get(name)
        if not tool:
            return f"Error : tool '{name}' not found"
        try:
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            return str(tool["func"](**arguments))
        except Exception as e:
            return f"Error executing tool '{name}': {e}"
