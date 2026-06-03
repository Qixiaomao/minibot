# Nanobot 骨架提炼

> 核心思想：**一个 AI Agent 就是一个无限循环，收消息 → 拼上下文 → 调 LLM → 执行工具 → 回消息。**
> 其余所有代码都是为这个循环服务的。

---

## 一、主循环（7 行伪代码，整个系统的心脏）

```python
while True:
    msg = channel.recv()                        # ① 从用户收消息
    context.add_message("user", msg.content)    # ② 放进上下文窗口

    if context.too_long():                      # ③ 上下文超长？压缩旧消息
        context.consolidate(agent)

    reply = agent.chat(context.get_prompt())    # ④ 组装上下文，调 LLM
    context.add_message("assistant", reply)     # ⑤ 存回上下文

    channel.send(reply)                         # ⑥ 回复用户
```

**记住这 6 步就够了。** 所有模块都是让这 6 步跑得更好的细节。

---

## 二、5 大组件及其接口契约

### 1. Channel（消息通道）—— 解决"消息从哪来、回哪去"

```
职责：统一 I/O 接口，屏蔽 Telegram / 微信 / 终端的差异
接口：
    recv()  → Message          # 阻塞，等一条用户消息
    send(msg: Message) → None   # 发一条回复给用户
    send_voice(path) → None     # (可选) 发语音
实现：TelegramChannel / StdinChannel / 未来: WechatChannel
关键设计：只关心 send/recv，不关心消息怎么处理
```

**迁移时：** 写一个新的 Channel 子类，实现 `recv()` 和 `send()` 就行。

### 2. ContextBuffer（上下文窗口）—— 解决"怎么给 LLM 喂对话历史"

```
职责：管理发给 LLM 的 messages 数组，控制长度
接口：
    add_message(role, content) → None     # 加一条消息
    get_prompt() → list[dict]             # 组装完整 messages 给 LLM
    estimate_tokens() → int               # 估算 token 数
    consolidate(agent) → None             # 用 LLM 压缩旧消息为摘要
内部结构：
    system_prompt ───────┐
    MEMORY.md 内容 ──────┤──→ 拼成 system message
    archived_summary ────┘
    messages[...] ──────────→ user/assistant/tool 消息列表
关键设计：get_prompt() 是唯一的输出口，组装逻辑集中在这里
```

**组装公式：**
```
system_message = system_prompt + memory_context + archived_summary
prompt = [system_message] + messages[-max_entries:]
```

**迁移时：** 理解 get_prompt() 的组装逻辑就够了，其他都是辅助。

### 3. Agent（LLM 调用循环）—— 解决"怎么跟 LLM 对话 + 执行工具"

```
职责：发 messages 给 LLM，自动处理 tool_calls 循环
接口：
    chat(messages: list[dict]) → str   # 输入 prompt，返回文本回复
内部循环：
    for round in 1..max_rounds:
        response = LLM(messages)
        if response has tool_calls:
            for each tool_call:
                result = tools.execute(name, args)  # 调用工具
                messages.append(tool_result)         # 结果塞回
            continue  # 把工具结果再发给 LLM
        else:
            return response.text  # 纯文本，结束
关键设计：
    - tools 注入方式：构造时传入 ToolRegistry
    - 防死循环：max_rounds=5
    - 工具执行结果追加为 role="tool" 的消息
```

**这就是 function calling 的核心套路，任何 LLM API 都是这个模式。**

### 4. ToolRegistry（工具注册表）—— 解决"怎么让 LLM 调用 Python 函数"

```
职责：注册工具、提供 schema 给 LLM、按名称执行工具
接口：
    register(name, func, description, parameters) → None
    get_schemas() → list[dict]              # OpenAI function-calling 格式
    execute(name, arguments) → str          # 执行并返回字符串结果
存储结构：
    {
        "get_time": {
            "func": get_time_function,
            "description": "获取当前日期和时间",
            "parameters": { "type": "object", "properties": {...} }
        },
        ...
    }
关键设计：
    - schema 是 JSON Schema，LLM 用它来决定何时调用、传什么参数
    - execute() 做参数解析 + 异常捕获，返回字符串
    - 注册和执行完全解耦：注册时只存函数引用，执行时才调用
```

**加工具只需要 3 样东西：**
1. 一个 Python 函数（接收参数，返回字符串）
2. 一个 JSON Schema（描述参数格式）
3. 一行 `registry.register(...)` 调用

### 5. MemoryStore（持久记忆）—— 解决"跨对话记住东西"

```
职责：文件级持久化，记忆在重启后不丢失
接口：
    read_memory() → str              # 读 MEMORY.md
    write_memory(content) → None     # 写 MEMORY.md
    get_memory_context() → str|None  # 读取并检查非空
    append_history(content) → None   # 追加摘要到 history.jsonl
    read_history(limit) → list       # 读最近 N 条历史
存储：
    workspace/memory/MEMORY.md      ← 长期事实（人可读可改）
    workspace/memory/history.jsonl  ← 对话摘要日志（追加写入）
关键设计：
    - 不用数据库，文件即状态
    - MEMORY.md 注入到 system prompt，所以 LLM "记得"这些事
    - history.jsonl 是 append-only 的，不会丢数据
```

---

## 三、组件之间的依赖关系（看这张图）

```
┌─────────────────────────────────────────────┐
│                   main.py                    │
│              (胶水层 / 组装层)                 │
│                                              │
│   channel ←──── recv()/send() ────→ 用户     │
│      ↓                                      │
│   context.add_message("user", msg)           │
│      ↓                                      │
│   context.too_long? → context.consolidate()  │
│      │                  ↑                    │
│      │              需要 agent               │
│      ↓                                      │
│   prompt = context.get_prompt()              │
│      │          ↑ 读取 MEMORY.md             │
│      │          ↑ 注入 archived_summary      │
│      ↓                                      │
│   reply = agent.chat(prompt)                 │
│      │          ↑ 传入 tools (ToolRegistry)  │
│      │          ↓                            │
│      │     LLM 返回 tool_calls 时            │
│      │     → tools.execute(name, args)       │
│      ↓                                      │
│   context.add_message("assistant", reply)    │
│      ↓                                      │
│   channel.send(reply) → 用户                 │
└─────────────────────────────────────────────┘
```

**依赖方向：main → 所有组件，组件之间互不依赖。**
- agent 不知道 channel 的存在
- channel 不知道 context 的存在
- context 通过参数持有 memory（可选）
- 只有 main.py 知道全局的组装方式

---

## 四、扩展点速查表

| 我想... | 改哪里 | 怎么改 |
|---------|--------|--------|
| 换个 LLM（如 OpenAI/Claude） | agent.py | 换 base_url 和 model |
| 加一个新工具 | builtin_tools.py | 写函数 + 注册 |
| 换消息平台（如微信） | channel.py | 写新 Channel 子类 |
| 改人设/角色 | main.py | 改 system_prompt 字符串 |
| 改上下文窗口大小 | main.py | 改 max_entries / max_tokens |
| 换持久化方式（如 Redis） | memory.py | 重写 MemoryStore 类 |
| 加图片/语音支持 | channel.py + agent.py | channel 加 recv 图片，agent 加多模态 |

---

## 五、从零复写的最小步骤

如果你要从空白文件重写一个 nanobot，按这个顺序：

```
第 1 步：写一个 while True 循环，能收终端输入、打印回来
         → 只需要 input() + print()

第 2 步：接上 LLM，把用户输入发过去，打印回复
         → requests.post(chat/completions)

第 3 步：加 tool_calls 处理循环
         → 检测 finish_reason == "tool_calls"，执行，再发

第 4 步：抽一个 ToolRegistry，用 schema 注册工具
         → register / get_schemas / execute

第 5 步：抽 ContextBuffer，管理 messages 窗口
         → add_message / get_prompt / consolidate

第 6 步：抽 Channel 抽象，换成 Telegram
         → recv / send 接口

第 7 步：加 MemoryStore，MEMORY.md 注入 system prompt
         → read_memory / write_memory / get_memory_context
```

**每一步都能独立跑通、独立测试。** 这就是渐进式构建 nanobot 的方式。

---

## 六、你的 minibot 目前的状态

| 组件 | 完成度 | 缺什么 |
|------|--------|--------|
| Agent | ✅ 基本完成 | 缺错误重试、流式输出 |
| ContextBuffer | ✅ 基本完成 | 启动时没加载 history |
| ToolRegistry | ✅ 基本完成 | 缺工具权限控制 |
| MemoryStore | ✅ 基本完成 | MEMORY.md 为空，没实际使用 |
| Channel (Telegram) | ✅ 基本完成 | 没错误处理，send_tool_result 未调用 |
| Channel (Stdin) | ✅ 存在但未接入 | main.py 没用它 |
| TTS | ⏸️ 写好了没接 | 需要接入主循环 |
| main.py 胶水层 | ⚠️ 有硬编码密钥 | 需要 env 变量 |
