# 🐱 MiniBot

**[中文](#中文)** | **[English](#english)**

---

<a id="中文"></a>
## 中文

一个轻量级的 AI 聊天机器人框架，基于 MiMo 大模型，支持工具调用（Function Calling）和长期记忆。

### 项目架构

```
┌─────────────────────────────────────────────────────┐
│                     main.py                         │
│                   (入口 & 胶水层)                    │
└───────┬──────────┬──────────┬──────────┬────────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ channel  │ │  agent   │ │ context  │ │  memory  │
│ 消息通道  │ │ LLM 调用 │ │ 上下文管理│ │ 长期记忆  │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │            │
     │            ▼            │            │
     │     ┌──────────┐       │            │
     │     │  tools   │       │            │
     │     │ 工具注册表 │       │            │
     │     └────┬─────┘       │            │
     │          │             │            │
     │          ▼             │            │
     │   ┌────────────┐      │            │
     │   │builtin_tools│      │            │
     │   │ 内置工具集   │      │            │
     │   └────────────┘      │            │
     │                       │            │
     ▼                       ▼            ▼
┌──────────────────────────────────────────────────┐
│               Telegram / Stdin                    │
│                  用户交互层                        │
└──────────────────────────────────────────────────┘
```

### 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| **Channel** | `channel.py` | 消息通道抽象层，支持 Telegram Bot 和终端 Stdin |
| **Agent** | `agent.py` | LLM 调用 + Function Calling 循环，自动执行工具并回传结果 |
| **Context** | `context.py` | 滑动窗口上下文管理，超长时自动压缩摘要 |
| **Memory** | `memory.py` | 文件级长期记忆（MEMORY.md + history.jsonl） |
| **Tools** | `tools.py` | 工具注册表，提供 OpenAI Function Calling 格式的 schema |
| **Built-in Tools** | `builtin_tools.py` | 内置工具：时间查询、计算器、文件读写、命令执行 |
| **TTS** | `tts.py` | MiMo-V2.5-TTS 语音合成（可选） |

### 工作流程

```
用户消息 → Channel.recv()
              ↓
         ContextBuffer.add_message()
              ↓
         token 超限？ → 是 → consolidate() 压缩摘要
              ↓ 否
         Agent.chat(messages)
              ↓
         LLM 返回 tool_calls？
              ├─ 是 → 执行工具 → 结果塞回 messages → 再调 LLM（循环）
              └─ 否 → 返回文本回复
              ↓
         Channel.send() → 用户
```

### 快速开始

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的密钥：

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `TELEGRAM_TOKEN` | Telegram Bot Token（从 @BotFather 获取） |
| `MIMO_API_KEY` | MiMo API 密钥 |
| `MIMO_BASE_URL` | MiMo API 地址 |
| `MIMO_MODEL` | 模型名称，默认 `mimo-v2.5-pro` |

#### 3. 运行

```bash
python main.py
```

### 内置工具

| 工具 | 功能 |
|------|------|
| `get_time` | 获取当前日期时间 |
| `calculator` | 数学表达式计算 |
| `read_file` | 读取本地文件（workspace 内） |
| `write_file` | 写入本地文件（workspace 内） |
| `exec` | 执行 shell 命令（30s 超时） |

---

<a id="english"></a>
## English

A lightweight AI chatbot framework powered by MiMo LLM, with support for Function Calling and long-term memory.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                     main.py                         │
│                 (Entry & Glue Layer)                │
└───────┬──────────┬──────────┬──────────┬────────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ channel  │ │  agent   │ │ context  │ │  memory  │
│ Messaging│ │ LLM Call │ │ Context  │ │  Long-   │
│ Channels │ │ + Tools  │ │ Manager  │ │  Term    │
└────┬─────┘ └────┬─────┘ └────┬─────┘ │  Memory  │
     │            │            │       └────┬─────┘
     │            ▼            │            │
     │     ┌──────────┐       │            │
     │     │  tools   │       │            │
     │     │  Tool    │       │            │
     │     │ Registry │       │            │
     │     └────┬─────┘       │            │
     │          │             │            │
     │          ▼             │            │
     │   ┌────────────┐      │            │
     │   │builtin_tools│      │            │
     │   │  Built-in   │      │            │
     │   │   Tools     │      │            │
     │   └────────────┘      │            │
     │                       │            │
     ▼                       ▼            ▼
┌──────────────────────────────────────────────────┐
│               Telegram / Stdin                    │
│                  User Interface                   │
└──────────────────────────────────────────────────┘
```

### Core Modules

| Module | File | Description |
|--------|------|-------------|
| **Channel** | `channel.py` | Messaging abstraction layer, supports Telegram Bot and terminal Stdin |
| **Agent** | `agent.py` | LLM invocation + Function Calling loop, auto-executes tools and feeds results back |
| **Context** | `context.py` | Sliding-window context management, auto-compresses into summary when exceeding token limit |
| **Memory** | `memory.py` | File-based long-term memory (MEMORY.md + history.jsonl) |
| **Tools** | `tools.py` | Tool registry, provides OpenAI Function Calling format schemas |
| **Built-in Tools** | `builtin_tools.py` | Built-in tools: time query, calculator, file read/write, command execution |
| **TTS** | `tts.py` | MiMo-V2.5-TTS voice synthesis (optional) |

### Workflow

```
User message → Channel.recv()
                  ↓
             ContextBuffer.add_message()
                  ↓
             Token limit exceeded? → Yes → consolidate() compress into summary
                  ↓ No
             Agent.chat(messages)
                  ↓
             LLM returns tool_calls?
                  ├─ Yes → Execute tools → Feed results back into messages → Call LLM again (loop)
                  └─ No  → Return text response
                  ↓
             Channel.send() → User
```

### Quick Start

#### 1. Install dependencies

```bash
pip install -r requirements.txt
```

#### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Telegram Bot Token (get from @BotFather) |
| `MIMO_API_KEY` | MiMo API key |
| `MIMO_BASE_URL` | MiMo API endpoint |
| `MIMO_MODEL` | Model name, defaults to `mimo-v2.5-pro` |

#### 3. Run

```bash
python main.py
```

### Built-in Tools

| Tool | Function |
|------|----------|
| `get_time` | Get current date and time |
| `calculator` | Evaluate math expressions |
| `read_file` | Read local files (within workspace) |
| `write_file` | Write local files (within workspace) |
| `exec` | Execute shell commands (30s timeout) |

---

## License

MIT
