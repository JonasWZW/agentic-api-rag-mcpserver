# Agentic API RAG MCP Server

让 AI 编码助手真正理解并利用团队的私有 API。

## Core Features

- **🤖 Agentic Smart Query**: LangChain/LangGraph-based intelligent Agent with natural language intent understanding
- **📚 RAG Vector Retrieval**: Chroma vector database + OpenAI Embeddings for semantic API search
- **🕸️ Knowledge Graph**: NetworkX-based API relationship graph for understanding dependencies
- **🔌 MCP Protocol**: Standard MCP protocol implementation for Cursor, Windsurf, Cline integration
- **🌐 Multi-Domain Support**: SubAgent architecture for domain-specific (user, order, payment) API management

## Use Cases

```
User: "How to call the user login API?"
AI:   "Found user login API:
       POST /api/v1/users/login

       Parameters: username(string), password(string)

       Example:
       requests.post('/api/v1/users/login',
                     json={'username': 'xxx', 'password': 'xxx'})"
```

- **Team Internal API Docs**: Let AI assistants understand team's private APIs
- **API Exploration**: Natural language search and discovery
- **Code Generation**: Auto-generate API calling code
- **API Comparison**: Compare differences between APIs

## Quick Start

### Requirements

- Python 3.10+
- OpenAI API Key (or compatible LLM)

### Installation

```bash
# Install from PyPI
pip install agentic-api-rag-mcpserver

# Or install from source
git clone https://github.com/your-repo/agentic-api-rag-mcpserver.git
cd agentic-api-rag-mcpserver
pip install -e .
```

### Configuration

Create `config/settings.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "openai"
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"

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

### Running

```bash
# Use built-in sample OpenAPI spec
python main.py

# Use custom spec
python main.py /path/to/your/openapi.yaml
```

### Using in Cursor

1. Open Cursor Settings
2. Find MCP Servers configuration
3. Add:

```json
{
  "agentic-api-rag": {
    "command": "python",
    "args": ["/path/to/main.py", "/path/to/your/api.yaml"]
  }
}
```

## MCP Tools

| Tool | Description | Example |
|------|-------------|---------|
| `query_agent` | Main entry: Natural language API query | `"show me user login API"` |
| `search_apis` | Direct API search | `{"query": "login", "top_k": 10}` |
| `get_api_detail` | Get API details | `{"api_id": "user_login"}` |
| `list_apis` | List APIs | `{"tags": ["user"], "limit": 50}` |

## Intent Types

| Intent | Description | Example |
|--------|-------------|---------|
| `QUERY` | Query API info | "Where is the login API?" |
| `CALL` | Call/Execute API | "Call the login API" |
| `UNDERSTAND` | Understand API原理 | "How does payment work?" |
| `COMPARE` | Compare APIs | "What's the difference between v1 and v2?" |
| `RECOMMEND` | Recommend APIs | "Any similar APIs?" |
| `DEBUG` | Debug issues | "Why did the call fail?" |

## Project Structure

```
agentic-api-rag-mcpserver/
├── src/
│   ├── mcp_server/           # MCP Server implementation
│   ├── agents/               # Agent layer
│   ├── knowledge_graph/      # Knowledge graph
│   ├── rag/                  # RAG engine
│   ├── models/               # Data models
│   └── config/               # Configuration
│
├── apis/                     # Sample OpenAPI specs
├── config/                   # Configuration files
├── main.py                   # Entry point
├── pyproject.toml            # Project config
└── README.md                 # This file
```

## Contributing

Issues and Pull Requests are welcome!

## License

MIT License - see [LICENSE](./LICENSE) for details

---

If you find this project helpful, please ⭐ Star!
