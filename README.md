# Agentic API RAG MCP Server

[English](./README_EN.md) | 中文

让 AI 编码助手真正理解并利用团队的私有 API。

[![PyPI Version](https://img.shields.io/pypi/v/agentic-api-rag-mcpserver)](https://pypi.org/project/agentic-api-rag-mcpserver/)
[![Python Version](https://img.shields.io/pypi/pyversions/agentic-api-rag-mcpserver)](https://pypi.org/project/agentic-api-rag-mcpserver/)
[![License](https://img.shields.io/pypi/l/agentic-api-rag-mcpserver)](./LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/your-repo/agentic-api-rag-mcpserver)](https://github.com/your-repo/agentic-api-rag-mcpserver/stargazers)

## 核心特性

- **🤖 Agentic 智能查询**: 基于 LangChain/LangGraph 的智能 Agent，支持自然语言理解用户意图
- **📚 RAG 向量检索**: Chroma 向量数据库 + OpenAI Embeddings，实现语义级别的 API 搜索
- **🕸️ 知识图谱**: 基于 NetworkX 的 API 关系图谱，理解 API 之间的依赖和关联
- **🔌 MCP 协议**: 标准 MCP 协议实现，无缝集成 Cursor、Windsurf、Cline 等 AI 编码工具
- **🌐 多领域支持**: SubAgent 架构，支持按业务领域（user、order、payment 等）分组管理

## 应用场景

```
用户: "查一下用户登录接口怎么调用"
AI:   "找到用户登录 API:
       POST /api/v1/users/login

       参数: username(string), password(string)

       示例代码:
       requests.post('/api/v1/users/login',
                     json={'username': 'xxx', 'password': 'xxx'})"
```

- **团队内部 API 文档**: 让 AI 助手理解团队私有 API
- **API 探索**: 自然语言搜索和发现 API
- **代码生成**: 自动生成 API 调用代码
- **API 对比**: 比较不同 API 的差异

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                   AI Coding Tool (Cursor/Windsurf/Cline)   │
└─────────────────────────────────┬───────────────────────────┘
                                  │ MCP Protocol
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                        MCP Server                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Manager Agent (Supervisor)              │   │
│  │  • 意图识别 (Intent Classification)                 │   │
│  │  • 路由决策 (Route Decision)                        │   │
│  │  • 结果聚合 (Result Aggregation)                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ SubAgent A    │       │ SubAgent B    │       │ SubAgent ...  │
│ (user domain) │       │ (order domain)│       │               │
│ • RAG 查询    │       │ • RAG 查询    │       │ • RAG 查询    │
└───────────────┘       └───────────────┘       └───────────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  ▼
        ┌───────────────────────────────────────────────────┐
        │              Knowledge Graph (NetworkX)          │
        │  API ──depends_on──► API                        │
        │  API ──similar_to──► API                        │
        │  API ──has_tag─────► Tag                        │
        └───────────────────────────────────────────────────┘
```

## 快速开始

### 前置要求

- Python 3.10+
- OpenAI API Key (或其他兼容的 LLM)

### 安装

```bash
# 从 PyPI 安装
pip install agentic-api-rag-mcpserver

# 或从源码安装
git clone https://github.com/your-repo/agentic-api-rag-mcpserver.git
cd agentic-api-rag-mcpserver
pip install -e .
```

### 配置

创建 `config/settings.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "openai"
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"  # 或直接填入 API Key

mcp:
  server_name: "agentic-api-rag"
  version: "1.0.0"

rag:
  vector_store: "chroma"
  embedding_model: "text-embedding-ada-002"
  chunk_size: 1000
  top_k: 5

kg:
  graph_type: "networkx"
  default_depth: 2
```

### 运行

```bash
# 使用内置示例 OpenAPI 规范
python main.py

# 使用自定义规范
python main.py /path/to/your/openapi.yaml

# 指定多个规范
python main.py api1.yaml api2.yaml api3.yaml
```

### 在 Cursor 中使用

1. 打开 Cursor 设置
2. 找到 MCP Servers 配置
3. 添加:

```json
{
  "agentic-api-rag": {
    "command": "python",
    "args": ["/path/to/main.py", "/path/to/your/api.yaml"]
  }
}
```

## MCP 工具

| 工具 | 说明 | 示例 |
|------|------|------|
| `query_agent` | 主入口：自然语言查询 API | `"查一下用户登录接口"` |
| `search_apis` | 直接搜索 API | `{"query": "登录", "top_k": 10}` |
| `get_api_detail` | 获取 API 详情 | `{"api_id": "user_login"}` |
| `list_apis` | 列出 API | `{"tags": ["user"], "limit": 50}` |

## 意图类型

| 意图 | 说明 | 示例 |
|------|------|------|
| `QUERY` | 查询 API 信息 | "用户登录接口在哪里？" |
| `CALL` | 调用/执行 API | "帮我调用登录接口" |
| `UNDERSTAND` | 理解 API 原理 | "支付接口怎么工作的？" |
| `COMPARE` | 比较 API 差异 | "v1 和 v2 有什么区别？" |
| `RECOMMEND` | 推荐相关 API | "有什么类似的接口吗？" |
| `DEBUG` | 调试问题 | "为什么调用失败了？" |

## 项目结构

```
agentic-api-rag-mcpserver/
├── src/
│   ├── mcp_server/           # MCP Server 实现
│   │   ├── server.py         # 服务器入口
│   │   ├── tools.py          # 工具定义
│   │   ├── resources.py      # 资源定义
│   │   └── prompts.py        # 提示定义
│   │
│   ├── agents/               # Agent 层
│   │   ├── manager.py        # Manager Agent (总控)
│   │   ├── sub_agent.py      # SubAgent (领域 Agent)
│   │   ├── intent.py        # 意图分类器
│   │   └── router.py        # 路由决策
│   │
│   ├── knowledge_graph/      # 知识图谱
│   │   ├── graph.py         # NetworkX 图谱
│   │   ├── builder.py       # 图谱构建器
│   │   └── queries.py       # 图查询接口
│   │
│   ├── rag/                 # RAG 引擎
│   │   ├── parser.py        # OpenAPI 解析器
│   │   ├── embedder.py      # 向量化模块
│   │   ├── store.py         # Chroma 存储
│   │   └── retriever.py     # 检索器
│   │
│   ├── models/              # 数据模型
│   │   ├── api_spec.py      # API 规格模型
│   │   ├── agent.py        # Agent 模型
│   │   └── graph.py         # 图谱模型
│   │
│   └── config/              # 配置
│       └── settings.py      # 配置加载
│
├── apis/                    # OpenAPI 示例规范
│   └── sample/
│       └── sample.yaml
│
├── config/                  # 配置文件
│   └── settings.yaml
│
├── main.py                  # 入口文件
├── pyproject.toml           # 项目配置
└── README.md                # 本文件
```

## 扩展开发

### 添加新的 SubAgent

```python
from src.agents import SubAgent

# 创建领域 Agent
payment_agent = SubAgent(
    name="payment_subagent",
    domain="payment",
    tags=["payment", "transaction"],
    retriever=retriever,
)

# 注册到 Manager
manager.register_subagent(payment_agent)
```

### 使用不同的 LLM

```python
# 使用 ChatGLM
from langchain_community.chat_models import ChatGLM

llm = ChatGLM(
    model_name="chatglm_pro",
    api_key="your-key",
    base_url="http://localhost:8000/v1"
)
```

### 自定义图谱关系

```python
from src.models import EdgeType

# 添加自定义边类型
kg.add_edge(source_api, target_api, type=EdgeType.DEPENDS_ON, weight=0.8)
```

## 常见问题

### Q: 支持哪些 OpenAPI 版本？
A: 支持 OpenAPI 3.0.x 和 2.x (Swagger)

### Q: 需要自己部署向量数据库吗？
A: 不需要，默认使用 Chroma 本地文件存储

### Q: 可以不使用 LLM 吗？
A: 可以，系统提供 keyword fallback 模式，但仍建议使用 LLM 以获得最佳体验

### Q: 支持哪些 AI 编码工具？
A: Cursor、Windsurf、Cline、Claude Desktop 等支持 MCP 协议的工具

## 相关文档

- [Model Context Protocol](https://modelcontextprotocol.io)
- [LangChain Documentation](https://python.langchain.com)
- [Chroma Vector Database](https://docs.trychroma.com)
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)

## 贡献

欢迎提交 Issue 和 Pull Request！

## License

MIT License - see [LICENSE](./LICENSE) for details

---

如果这个项目对你有帮助，欢迎 ⭐ Star！
