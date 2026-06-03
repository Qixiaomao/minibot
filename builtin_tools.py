import os 
import subprocess
import datetime
from pathlib import Path

def register_builtin_tools(registry, workspace="."):
      """把 5 个内置工具注册到 registry。workspace 限制文件操作范围。"""
      ws = Path(workspace).resolve()

      # 1. get_time
      def get_time(timezone=None):
          """获取当前时间"""
          now = datetime.datetime.now()
          return now.strftime("%Y-%m-%d %H:%M:%S")

      registry.register(
          "get_time", get_time,
          description="获取当前日期和时间",
          parameters= {"type": "object", 
                      "properties": {"timezone": {"type": "string", "description": "时区，如Asia/Shanghai（可选）"}
          }},
          )
      
        # 2. calculator
      def calculator(expression):
          """数学计算，只允许安全的数学表达式"""
          allowed_chars = set("0123456789+-*/.() %")
          if not all(c in allowed_chars for c in expression):
              return f"Error: 包含不允许的字符，只支持数学运算"
          try:
              result = eval(expression)
              return str(result)
          except Exception as e:
              return f"Error: 计算失败: {e}"

      registry.register(
          "calculator", calculator,
          description="计算数学表达式，支持加减乘除和括号",
          parameters={"type": "object", 
                      "properties": {"expression": {"type": "string", "description": "数学表达式，如'123*456+789'"}}, 
                       "required": ["expression"]},
      )
      
      # 3. read_file
      def read_file(path):
          """读取文件内容，限制在 workspace 内"""
          target = (ws / path).resolve()
          if not str(target).startswith(str(ws)):
              return "Error: 路径超出工作目录范围"
          if not target.exists():
              return f"Error: 文件不存在: {path}"
          try:
              content = target.read_text(encoding="utf-8")
              return content[:5000]  # 限制返回长度
          except Exception as e:
              return f"Error: 读取失败: {e}"

      registry.register(
          "read_file", read_file,
          description="读取本地文件内容",
          parameters={"type": "object", "properties": {
              "path": {"type": "string", "description":
  "文件路径，相对于工作目录"}
          }, "required": ["path"]},
      )
      
      # 4. write_file
      def write_file(path, content):
          """写入文件，限制在 workspace 内"""
          target = (ws / path).resolve()
          if not str(target).startswith(str(ws)):
              return "Error: 路径超出工作目录范围"
          try:
              target.parent.mkdir(parents=True, exist_ok=True)
              target.write_text(content, encoding="utf-8")
              return f"OK: 已写入 {path}"
          except Exception as e:
              return f"Error: 写入失败: {e}"

      registry.register(
          "write_file", write_file,
          description="写入内容到本地文件",
          parameters={"type": "object", "properties": {
              "path": {"type": "string", "description": "文件路径"},
              "content": {"type": "string", "description": "要写入的内容"}
          }, "required": ["path", "content"]},
      )
      
      # 5. exec
      def exec_command(command):
          """执行 shell 命令，限制工作目录，超时 30 秒"""
          try:
              result = subprocess.run(
                  command, shell=True, capture_output=True, text=True,
                  timeout=30, cwd=str(ws),
              )
              output = result.stdout + result.stderr
              return output[:3000] if output else "(无输出)"
          except subprocess.TimeoutExpired:
              return "Error: 命令执行超时（30s）"
          except Exception as e:
              return f"Error: 执行失败: {e}"

      registry.register(
          "exec", exec_command,
          description="执行 shell 命令",
          parameters={"type": "object", "properties": {
              "command": {"type": "string", "description": "要执行的命令"}
          }, "required": ["command"]},
      )