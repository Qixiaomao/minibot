"""memory — 从本地文件加载长期记忆 (对标 nanobot Memory skill)"""

# 读取 SOUL.md / USER.md / MEMORY.md → 拼成 system prompt 文本

import json
import os
from pathlib import Path
from datetime import datetime



class MemoryStore:
    """文件级记忆：MEMORY.md (长期事实) + history.jsonl (对话摘要日志)"""
    def __init__(self, workspace = "."):
        self.workspace = Path(workspace).resolve()
        self.memory_dir = self.workspace / "memory"
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "history.jsonl"
        self.memory_dir.mkdir(parents=True, exist_ok=True)



    def read_memory(self):
        """读取MEMORY.md内容，不存在返回空字符串"""
        try:
            return self.memory_file.read_text(encoding = "utf-8")
        except FileNotFoundError:
            return ""
        
    def write_memory(self, content):
        """写入 MEMORY.md """
        self.memory_file.write_text(content, encoding = "utf-8")
        
    def get_memory_context(self):
        """返回 MEMORY.md 内容，用于注入 system prompt。空文件返回 None。"""
        content = self.read_memory()
        return content.strip() if content.strip() else None
    
    def append_history(self, content):
        """追加一条记录到 history.jsonl"""
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              "content": content,
        }
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
    def read_history(self, limit = 10):
        """读取最近 N 条历史记录"""
        entries = [] 
        try:
            with open(self.history_file, "r", encoding = "utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except FileNotFoundError:
            pass
        return entries[-limit:]
    