# Agentic API RAG MCP Server - 设计文档

## 1. 项目概述

### 1.1 项目背景

让 AI 编码助手真正理解并利用团队的私有 API。

### 1.2 核心价值

- 将分散的 OpenAPI 规格文件转化为可检索的 API 知识库
- 通过 MCP 协议无缝集成到 Cursor、Windsurf、Cline 等 AI 编码工具
- 增加 Agentic 包装层，实现智能意图分析和结果整合

### 1.3 技术选型

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| Agent 框架 | LangChain / LangGraph | 官方推荐的 Agent 编排框架 |
| MCP 协议 | mcp-python | Python 实现的 MCP Server SDK |
| 知识图谱 | NetworkX | 内存图结构，无需额外数据库 |
| 向量存储 | Chroma | 轻量级向量数据库 |
| OpenAPI 解析 | openapi-parser / swagger-parser | OpenAPI 规格解析 |
| LLM 集成 | LangChain ChatGLM / OpenAI | 支持多种 LLM 后端 |

---

## 2.3 详细数据流

### 2.3.1 整体数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户查询入口                                     │
│                   (来自 Cursor/Windsurf/Cline 的自然语言)                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Step 1: MCP 协议层                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MCP Request → 解析请求参数 → 转换为内部格式                         │   │
│  │  • 工具调用: search_apis, query_agent                              │   │
│  │  • 资源请求: 获取 API 规格                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Step 2: Manager Agent (入口)                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  2.1 请求预处理                                                       │   │
│  │      • 提取查询文本                                                  │   │
│  │      • 获取对话上下文                                                │   │
│  │      • 解析元信息 (filters, api_ids)                                 │   │
│  │                                                                       │   │
│  │  2.2 意图分类 IntentClassifier                                       │   │
│  │      • 分析用户真实意图                                              │   │
│  │      • 输出: Intent + 置信度                                         │   │
│  │                                                                       │   │
│  │  2.3 上下文构建                                                       │   │
│  │      • 从 Knowledge Graph 获取关联 API                               │   │
│  │      • 合并、去重、排序                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────────┐
              │           Step 3: 路由决策                 │
              │  ┌─────────────────────────────────────┐   │
              │  │  • 根据 Intent 选择处理路径          │   │
              │  │  • 根据领域标签选择 SubAgent         │   │
              │  │  • 决定是否需要多 SubAgent 协作     │   │
              │  └─────────────────────────────────────┘   │
              └───────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ SubAgent A    │       │ SubAgent B    │       │ SubAgent ...  │
│ (user domain) │       │ (order domain)│       │               │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                         │
        └───────────────────────┼─────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Step 4: SubAgent 执行                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  4.1 查询处理 Query Processing                                       │   │
│  │      • Query 规范化                                                  │   │
│  │      • Query 扩展 (可选)                                             │   │
│  │                                                                       │   │
│  │  4.2 RAG 检索                                                         │   │
│  │      • 向量相似度搜索                                                │   │
│  │      • 关键词过滤                                                    │   │
│  │      • 结果合并                                                      │   │
│  │                                                                       │   │
│  │  4.3 结果生成 Result Generator                                       │   │
│  │      • 提取关键信息                                                  │   │
│  │      • 生成自然语言回复                                              │   │
│  │      • 附加 API 调用建议                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Step 5: 结果聚合                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  5.1 多 SubAgent 结果合并                                             │   │
│  │      • 去重策略                                                      │   │
│  │      • 优先级排序                                                    │   │
│  │                                                                       │   │
│  │  5.2 格式化输出                                                       │   │
│  │      • 结构化 JSON                                                   │   │
│  │      • Markdown 渲染                                                 │   │
│  │      • 源码示例生成                                                  │   │
│  │                                                                       │   │
│  │  5.3 响应发送                                                         │   │
│  │      → MCP Response → AI Coding Tool                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3.2 Manager Agent 工作方式 (Supervisor 模式)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Manager Agent = Supervisor Agent                         │
│                    (类似 LangGraph 的 Supervisor 模式)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  定义: SubAgent 作为 "Tool"                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  @tool                                                                 │   │
│  │  def call_user_subagent(query: str) -> str:                          │   │
│  │      """处理用户领域相关的 API 查询"""                                │   │
│  │      return user_subagent.execute(query)                             │   │
│  │                                                                       │   │
│  │  @tool                                                                 │   │
│  │  def call_order_subagent(query: str) -> str:                        │   │
│  │      """处理订单领域相关的 API 查询"""                                │   │
│  │      return order_subagent.execute(query)                            │   │
│  │                                                                       │   │
│  │  ...  (每个 SubAgent 注册为一个 tool)                                  │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LLM Supervisor 循环                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  while not done:                                                      │   │
│  │      # 1. LLM 生成 action                                            │   │
│  │      action = llm.generate(                                           │   │
│  │          context=current_context,                                    │   │
│  │          tools=available_subagents  # SubAgent 当工具用              │   │
│  │      )                                                               │   │
│  │                                                                       │   │
│  │      # 2. 执行 action                                                 │   │
│  │      if action.tool_name:                                            │   │
│  │          result = action.tool_name.execute(action.args)             │   │
│  │          context.add(result)                                        │   │
│  │      else:                                                           │   │
│  │          done = True                                                 │   │
│  │          final_answer = action                                       │   │
│  │                                                                       │   │
│  │  return final_answer                                                 │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
```

### 2.3.3 Manager Agent 内部数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Manager Agent 详细数据流                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         2.3.3.1 请求预处理 (Preprocessor)                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  输入: MCP Request                                                    │   │
│  │  ┌─────────────┬─────────────┬─────────────┬─────────────┐          │   │
│  │  │ query       │ filters     │ api_ids     │ context     │          │   │
│  │  │ (自然语言)   │ (tag/path)  │ (指定API)   │ (对话历史)   │          │   │
│  │  └─────────────┴─────────────┴─────────────┴─────────────┘          │   │
│  │                                                                       │   │
│  │  处理:                                                                │   │
│  │  ① 提取 query 文本                                                   │   │
│  │  ② 解析 filters (可选: tag, path prefix, method)                    │   │
│  │  ③ 解析 api_ids (可选: 直接指定要查询的 API)                          │   │
│  │  ④ 获取历史上下文 (前 N 轮对话)                                       │   │
│  │                                                                       │   │
│  │  输出: PreprocessedRequest                                           │   │
│  │  { query, filters, api_ids, history_messages }                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    2.3.3.2 意图分类 (Intent Classifier)                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  输入: query + history                                               │   │
│  │                                                                       │   │
│  │  处理:                                                                │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  方式 A: LLM 直接分类 (推荐)                                  │   │   │
│  │  │  • 使用 langchain with structured output                     │   │   │
│  │  │  • 输出: {intent, confidence, reasoning, entities}           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  方式 B: 关键词匹配 (快速回退)                                │   │   │
│  │  │  • 预设意图模板 → 向量化 → 相似度匹配                        │   │   │
│  │  │  • 优点: 快速、便宜                                           │   │   │
│  │  │  • 缺点: 灵活度低                                             │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  输出: IntentResult                                                 │   │
│  │  { intent, confidence, reasoning, entities: [{type, value}] }      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    2.3.3.3 上下文构建 (Context Builder)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  输入: query + intent + filters                                     │   │
│  │                                                                       │   │
│  │  处理: 两条检索路径并行                                               │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────┐    ┌─────────────────────────┐         │   │
│  │  │   路径 A: 知识图谱       │    │   路径 B: RAG 引擎      │         │   │
│  │  │   (Knowledge Graph)     │    │   (RAG Engine)          │         │   │
│  │  ├─────────────────────────┤    ├─────────────────────────┤         │   │
│  │  │ ① 实体识别             │    │ ① 向量化 query         │         │   │
│  │  │    NER 提取 API 名     │    │    embedding(query)    │         │   │
│  │  │                         │    │                         │         │   │
│  │  │ ② 图查询               │    │ ② 向量检索             │         │   │
│  │  │    find_related()     │    │    similarity_search() │         │   │
│  │  │    depth=2            │    │    top_k=10            │         │   │
│  │  │                         │    │                         │         │   │
│  │  │ ③ 结果排序             │    │ ③ 结果过滤             │         │   │
│  │  │    by weight           │    │    by filters          │         │   │
│  │  │                         │    │                         │         │   │
│  │  │  输出: List[API]       │    │  输出: List[API]       │         │   │
│  │  │    (带图关系上下文)     │    │    (带语义相似度)       │         │   │
│  │  └─────────────────────────┘    └─────────────────────────┘         │   │
│  │                 │                              │                      │   │
│  │                 └──────────────┬───────────────┘                      │   │
│  │                                ▼                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │  合并 & 去重                                                       │   │   │
│  │  │  • union(set(kg_results), set(rag_results))                      │   │   │
│  │  │  • 按相关性权重合并                                               │   │   │
│  │  │  • 取 top K (默认 10)                                            │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                       │   │
│  │  输出: Context                                                       │   │
│  │  { apis: List[API], sources: ["graph", "rag", "direct"],           │   │
│  │      query_expansion: List[str] }                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      2.3.3.4 路由决策 (Router)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  输入: query + intent + context                                      │   │
│  │                                                                       │   │
│  │  决策逻辑:                                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  IF api_ids 直接指定 THEN                                    │   │   │
│  │  │     → 直接路由到对应领域的 SubAgent                          │   │   │
│  │  │  END IF                                                       │   │   │
│  │  │                                                               │   │   │
│  │  │  IF intent == COMPARE THEN                                    │   │   │
│  │  │     → 多 SubAgent 协作 (按 API tags 拆分)                   │   │   │
│  │  │  ELSE IF intent == RECOMMEND THEN                              │   │   │
│  │  │     → 跨 SubAgent 广播                                        │   │   │
│  │  │  ELSE                                                         │   │   │
│  │  │     → 单 SubAgent (选择 tag 匹配度最高的)                     │   │   │
│  │  │  END IF                                                       │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  输出: RouteDecision                                                │   │
│  │  { target_subagents: List[str], strategy: "single|parallel|chain",│   │
│  │      execution_order: List[str] }                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
```

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MCP Client (Cursor/Windsurf/Cline)                      │
│                         AI Coding Tools                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  │ MCP Protocol
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Server                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  接收请求 → 解析参数 → 调用 Manager Agent                              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Manager Agent (Supervisor)                              │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  1. 意图分析 (Intent Analysis)                                        │ │
│  │     • 分析用户想要什么（查API、调用、对比...）                         │ │
│  │     • 输出: intent + 相关领域(tags)                                   │ │
│  │                                                                       │ │
│  │  2. 路由决策 (Route Decision)                                        │ │
│  │     • 根据 tags 选择调用哪些 SubAgent                                 │ │
│  │     • SubAgent 在 Manager 看来就是"工具"                             │ │
│  │                                                                       │ │
│  │  3. SubAgent 调用 (SubAgent Invocation)                              │ │
│  │     • 类似 LLM 调用工具的方式                                        │ │
│  │     • parallel / sequential / chain 策略                            │ │
│  │                                                                       │ │
│  │  4. 结果聚合 (Result Aggregation)                                    │ │
│  │     • 合并多 SubAgent 返回                                           │ │
│  │     • 格式化输出                                                      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ SubAgent 1    │       │ SubAgent 2    │       │ SubAgent N    │
│ (user domain) │       │ (order domain)│       │               │
│               │       │               │       │               │
│ • RAG 查询    │       │ • RAG 查询    │       │ • RAG 查询    │
│ • 结果生成    │       │ • 结果生成    │       │ • 结果生成    │
└───────────────┘       └───────────────┘       └───────────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Manager Agent 结果聚合                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件说明

#### 2.2.1 MCP Server
- 负责与 AI 编码工具通信
- 暴露标准 MCP 工具和资源
- 协议版本: MCP v1.0
- **关键职责**: 只做协议转换和请求转发，不参与业务逻辑

#### 2.2.2 Manager Agent (Supervisor)
整个系统的核心调度层，**只负责调度，不做 RAG 查询**：

1. **意图识别 (Intent Classification)**
   - 理解用户查询的真实意图
   - 意图类型：QUERY、CALL、UNDERSTAND、COMPARE、RECOMMEND、DEBUG

2. **图谱查询 (Graph Query)**
   - 调用 Knowledge Graph 查找相关 API
   - 关联分析，获取上下文

3. **路由决策 (Route Dispatch)**
   - 根据业务领域选择合适的 SubAgent
   - 支持多 SubAgent 协作（parallel/sequential/chain）
   - **SubAgent 在 Manager 看来就是 "Tool"**

4. **结果整合 (Result Aggregation)**
   - 汇总各 SubAgent 结果
   - 去重、排序、格式化输出

#### 2.2.3 SubAgent Pool
每个 SubAgent 负责特定业务领域的 API 管理：

- 注册到 Manager Agent
- 维护该领域的 API 索引
- 执行具体查询和调用

#### 2.2.4 Knowledge Graph
基于 NetworkX 的内存图谱：

**Manager Agent 用图谱做什么:**
- Q1: 用户 query 中提到的 API，和哪些 API 有关联？
- Q2: 这个 API 依赖哪些其他 API？
- Q3: 哪些 API 可以完成类似的功能？
- Q4: 根据 tags 找到所有相关 API

**节点类型:**
- `API`: API 端点
- `Schema`: 数据模型
- `Tag`: 业务标签
- `Parameter`: 参数
- `Operation`: 操作类型

**边类型:**
| 边类型 | 说明 | 示例 |
|--------|------|------|
| DEPENDS_ON | 依赖关系 | login → depends → token |
| SIMILAR_TO | 语义相似 | login ↔ signin |
| PART_OF | 组合关系 | order_item → part_of order |
| CALLS | 调用关系 | create_order → calls pay |
| HAS_PARAM | 包含参数 | login → has_param password |
| USES_SCHEMA | 使用模型 | create → uses_schema Order |
| HAS_TAG | 拥有标签 | login → has_tag user |
| SAME_OP | 相同操作 | get_user, list_user |

#### 2.2.5 RAG Engine (SubAgent 内部使用)
每个 SubAgent 独立使用 RAG 引擎进行查询

**SubAgent 用 RAG 做什么:**
- Q1: 给定 query，找到最相关的 API 文档
- Q2: 只在特定 tag/domain 下搜索
- Q3: 根据 API ID 直接获取详细信息
- Q4: 批量获取多个 API 的文档

**文档分块策略 (Chunking):**

| 策略 | 说明 |
|------|------|
| Endpoint 分块 (推荐) | 每个 API Endpoint = 一个独立文档 |
| Schema 分块 (补充) | 每个数据模型 = 一个独立文档 |

**文档格式示例:**
```python
"""
[API: POST /api/v1/user/login]
[Summary: 用户登录]
[Tags: user, auth]

[Description]
用户登录接口，验证用户名密码，返回 token

[Request Parameters]
- username: string, required
- password: string, required

[Response]
{
    "token": "string",
    "expires_in": 7200
}

[Security]
需要 Bearer Token
"""
```

**RAG 查询流程:**
```python
class RAGEngine:

    def search(self, query: str, filters: dict, top_k: int = 5):
        # 1. 向量化 query
        query_embedding = self.embeddings.embed_query(query)

        # 2. 相似度搜索
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=top_k * 2,
            filter=filters
        )

        # 3. 结果过滤
        filtered = self._apply_filters(results, filters)

        # 4. 排序返回
        return filtered[:top_k]
```

**向量存储:** Chroma (轻量，易用)

---

## 3. 数据模型

### 3.1 API 实体

```python
class APIEntity:
    id: str                          # 唯一标识
    path: str                       # API 路径
    method: str                     # HTTP 方法
    summary: str                    # 摘要
    description: str                # 详细描述
    tags: List[str]                 # 业务标签
    parameters: List[Parameter]     # 请求参数
    request_schema: Schema          # 请求体
    response_schema: Schema         # 响应体
    security: List[str]             # 安全要求
    deprecated: bool                # 是否废弃
```

### 3.2 图谱节点

```python
# NetworkX 节点属性
api_node = {
    "type": "API",
    "id": "user_get_profile",
    "path": "/api/v1/user/profile",
    "method": "GET",
    "summary": "获取用户资料",
    "tags": ["user"]
}

schema_node = {
    "type": "Schema",
    "id": "UserProfile",
    "properties": {...}
}
```

### 3.3 图谱边

```python
# NetworkX 边属性
edge = {
    "type": "depends_on",
    "weight": 0.8,
    "reason": "需要 auth token"
}
```

---

## 4. Agent 设计

### 4.1 Manager Agent

```python
class ManagerAgent:
    """Supervisor Agent - 总控 Agent"""

    def __init__(
        self,
        llm: BaseChatModel,
        sub_agents: Dict[str, SubAgent],
        knowledge_graph: APIGraph,
        rag_engine: RAGEngine
    ):
        self.llm = llm
        self.sub_agents = sub_agents
        self.kg = knowledge_graph
        self.rag = rag_graph
        self.intent_classifier = IntentClassifier(llm)

    async def process(self, query: str) -> AgentResponse:
        """处理用户查询"""

        # Step 1: 意图识别
        intent = await self.intent_classifier.classify(query)

        # Step 2: 知识图谱关联查询
        related_apis = self.kg.find_related(
            query,
            depth=2,
            intent=intent
        )

        # Step 3: 选择 SubAgent
        target_subagent = self._route(query, intent)

        # Step 4: SubAgent 执行
        result = await target_subagent.execute(
            query=query,
            context=related_apis,
            intent=intent
        )

        # Step 5: 结果整合
        return self._aggregate(result, intent)
```

### 4.2 意图分类

#### 4.2.1 意图类型定义

```python
INTENT_TYPES = {

    "QUERY": {
        "description": "查询 API 信息",
        "examples": [
            "用户登录接口在哪里？",
            "有哪些创建订单的 API？",
            "获取商品详情的接口怎么调用？"
        ],
        "response_type": "api_list"
    },

    "CALL": {
        "description": "调用/执行 API",
        "examples": [
            "帮我调用用户登录接口",
            "执行创建订单 API"
        ],
        "response_type": "api_response"
    },

    "UNDERSTAND": {
        "description": "理解 API 用途和原理",
        "examples": [
            "这个支付接口是怎么工作的？",
            "用户认证流程是怎样的？"
        ],
        "response_type": "explanation"
    },

    "COMPARE": {
        "description": "比较多个 API 的差异",
        "examples": [
            "v1 和 v2 版本的区别是什么？",
            "这两个接口哪个更好？"
        ],
        "response_type": "comparison"
    },

    "RECOMMEND": {
        "description": "推荐相关 API",
        "examples": [
            "有什么类似的接口吗？",
            "除了这个还有别的选择吗？"
        ],
        "response_type": "api_list"
    },

    "DEBUG": {
        "description": "调试/排查问题",
        "examples": [
            "为什么调用失败了？",
            "这个接口报错了怎么解决？"
        ],
        "response_type": "debug_guide"
    }
}
```

#### 4.2.2 意图分类器实现

```python
class Intent(Enum):
    QUERY = "query"           # 查询 API 信息
    CALL = "call"             # 请求调用 API
    UNDERSTAND = "understand" # 理解 API 用途
    COMPARE = "compare"       # 比较多个 API
    RECOMMEND = "recommend"   # 推荐相关 API
    DEBUG = "debug"           # 调试问题


@dataclass
class IntentResult:
    intent: str              # QUERY/CALL/UNDERSTAND/...
    confidence: float       # 0.0 - 1.0
    reasoning: str          # 分类理由
    entities: List[Entity]  # 识别的实体


@dataclass
class Entity:
    type: str       # domain/tag/api_name/operation
    value: str      # "user", "order", "login"
    confidence: float


class IntentClassifier:
    """基于 LLM 的意图分类器"""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.prompt = self._build_prompt()

    def _build_prompt(self) -> PromptTemplate:
        return PromptTemplate.from_template("""
            分析用户查询的意图。

            可选意图类型:
            - QUERY: 查询 API 信息
            - CALL: 调用/执行 API
            - UNDERSTAND: 理解 API 原理
            - COMPARE: 比较 API 差异
            - RECOMMEND: 推荐相关 API
            - DEBUG: 调试问题

            用户查询: {query}
            历史对话: {history}

            输出格式 (JSON):
            {{
                "intent": "QUERY",
                "confidence": 0.95,
                "reasoning": "用户询问登录接口位置...",
                "entities": [
                    {{"type": "domain", "value": "user"}},
                    {{"type": "operation", "value": "login"}}
                ]
            }}
        """)

    async def classify(self, query: str, history: str = "") -> IntentResult:
        """使用 LLM 进行意图分类"""
        chain = self.prompt | self.llm.with_structured_output(IntentResult)
        return await chain.ainvoke({"query": query, "history": history})


# 快速回退: 关键词匹配
KEYWORD_PATTERNS = {
    "QUERY": ["哪里", "怎么", "哪些", "什么接口", "找", "查询"],
    "CALL": ["调用", "执行", "请求", "调用"],
    "UNDERSTAND": ["是什么", "怎么工作", "原理", "流程"],
    "COMPARE": ["区别", "差异", "哪个好", "对比", "比较"],
    "RECOMMEND": ["推荐", "类似", "其他", "代替"],
    "DEBUG": ["错误", "失败", "报错", "问题", "解决"]
}
```

### 4.3 SubAgent

#### 4.3.1 SubAgent 内部数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SubAgent 内部数据流                                   │
│                   (每个 SubAgent 负责一个业务领域)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  输入: Manager 传递的任务                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  {                                                                       │   │
│  │    query: str,              // 原始用户查询                           │   │
│  │    domain: str,             // 业务领域 (user/order/payment)          │   │
│  │    intent: str,             // 意图类型 (QUERY/CALL/COMPARE...)        │   │
│  │    context: {               // 上下文（可选）                          │   │
│  │      related_apis: [],      // 来自其他 SubAgent 的关联 API            │   │
│  │      history: []            // 对话历史                                │   │
│  │    }                                                                        │   │
│  │  }                                                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 1: Query Processing (查询处理)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1.1 Query 规范化                                                    │   │
│  │      • 提取核心关键词                                                │   │
│  │      • 补充领域前缀 (e.g., "user login" → "user login api")         │   │
│  │      • 移除噪音词                                                    │   │
│  │                                                                       │   │
│  │  1.2 Query 扩展 (可选)                                               │   │
│  │      • 同义词扩展 (login → authenticate, signin)                    │   │
│  │      • 相关词扩展 (order → 订单, 购买)                               │   │
│  │                                                                       │   │
│  │  输出: ProcessedQuery                                                │   │
│  │  { normalized_query, expanded_queries, keywords }                      │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 2: RAG Retrieval (RAG 检索)                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  2.1 向量化                                                           │   │
│  │      • embedding = embed_model.encode(processed_query)              │   │
│  │                                                                       │   │
│  │  2.2 向量检索                                                         │   │
│  │      • results = vector_store.similarity_search(                     │   │
│  │      •     query=embedding,                                           │   │
│  │      •     filter={"domain": self.domain, "tag": self.domain},       │   │
│  │      •     top_k=10                                                  │   │
│  │      • )                                                             │   │
│  │                                                                       │   │
│  │  2.3 结果排序                                                         │   │
│  │      • 综合评分: semantic_score * keyword_boost                      │   │
│  │      • 取 top K (可配置，默认 5)                                      │   │
│  │                                                                       │   │
│  │  输出: RetrievalResults                                              │   │
│  │  { apis: List[API], scores: List[float], sources: List[str] }       │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 3: Result Generation (结果生成)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  3.1 结果筛选                                                         │   │
│  │      • 按相关性阈值过滤                                               │   │
│  │      • 按 intent 筛选:                                               │   │
│  │        - QUERY: 返回 API 列表                                         │   │
│  │        - CALL: 准备调用参数                                           │   │
│  │        - UNDERSTAND: 生成解释                                         │   │
│  │                                                                       │   │
│  │  3.2 内容生成 (基于 LLM)                                              │   │
│  │      prompt = f"""                                                    │   │
│  │        你是一个 API 专家。根据检索到的 API 信息，回答用户问题。         │   │
│  │                                                                       │   │
│  │        用户问题: {query}                                              │   │
│  │        意图类型: {intent}                                             │   │
│  │                                                                       │   │
│  │        相关 API:                                                      │   │
│  │        {format_apis(retrieved_apis)}                                   │   │
│  │                                                                       │   │
│  │        请生成回答:                                                    │   │
│  │      """                                                             │   │
│  │                                                                       │   │
│  │  3.3 附加信息                                                         │   │
│  │      • 可选的代码示例生成                                              │   │
│  │      • API 调用建议                                                   │   │
│  │                                                                       │   │
│  │  输出: SubAgentResult                                                │   │
│  │  {                                                                       │   │
│  │    answer: str,              // 自然语言回答                          │   │
│  │    apis: List[API],         // 引用的 API 列表                       │   │
│  │    code_examples: [],       // 代码示例（可选）                       │   │
│  │    suggestions: []          // 建议（可选）                          │   │
│  │  }                                                                        │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
```

#### 4.3.2 SubAgent 注册与调用机制

```python
class SubAgent:
    """业务领域 Agent"""

    def __init__(
        self,
        name: str,
        domain: str,
        llm: BaseChatModel,
        rag_engine: RAGEngine,
        apis: List[APIEntity]
    ):
        self.name = name           # "user_agent"
        self.domain = domain       # "user"
        self.tags = [domain]        # ["user", "auth"]
        self.llm = llm
        self.rag = rag_engine
        self.apis = apis

    def as_tool(self) -> Tool:
        """转换为 LangChain Tool"""
        return Tool(
            name=self.name,
            description=f"处理 {domain} 领域的 API 查询",
            func=self.execute,
            coroutine=self.aexecute
        )

    async def execute(
        self,
        query: str,
        context: List[APIEntity],
        intent: Intent
    ) -> SubAgentResult:
        """执行查询"""
        # 使用 RAG 检索相关 API
        # 结合图谱上下文
        # 返回结构化结果
```

#### 4.3.3 SubAgent 注册到 Manager

```python
class ManagerAgent:

    def __init__(self, llm, sub_agents: List[SubAgent]):
        # 将每个 SubAgent 转换为 Tool
        self.tools = [sa.as_tool() for sa in sub_agents]

        # 使用 LangGraph 的 Supervisor 模式
        self.agent = self._create_supervisor(llm, self.tools)

    def _create_supervisor(self, llm, tools):
        return SupervisorAgent(
            llm=llm,
            tools=tools,
            system_prompt=f"""
                你是一个 API 调度专家。
                根据用户查询，选择合适的 SubAgent 处理。

                可用 SubAgent: {tools_desc}
            """
        )
```

---

## 5. MCP 协议接口

### 5.1 工具 (Tools)

#### query_agent (主入口)
```python
{
    "name": "query_agent",
    "description": "主入口：通过自然语言查询 API 知识库",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "自然语言查询，如 '查一下用户登录接口'"
            },
            "filters": {
                "type": "object",
                "description": "可选的过滤条件",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "version": {"type": "string"},
                    "deprecated": {"type": "boolean"}
                }
            },
            "options": {
                "type": "object",
                "description": "额外选项",
                "properties": {
                    "include_examples": {
                        "type": "boolean",
                        "description": "是否包含代码示例",
                        "default": True
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5
                    }
                }
            }
        },
        "required": ["query"]
    }
}
```

#### search_apis
```python
{
    "name": "search_apis",
    "description": "直接搜索 API（不使用 Agent）",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "filters": {"type": "object"},
            "top_k": {"type": "integer", "default": 10}
        },
        "required": ["query"]
    }
}
```

#### get_api_detail
```python
{
    "name": "get_api_detail",
    "description": "获取指定 API 的完整信息",
    "input_schema": {
        "type": "object",
        "properties": {
            "api_id": {
                "type": "string",
                "description": "API 唯一标识，如 'login'"
            },
            "include_examples": {"type": "boolean"}
        },
        "required": ["api_id"]
    }
}
```

#### list_apis
```python
{
    "name": "list_apis",
    "description": "列出所有 API 或按 tag 过滤",
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 50}
        }
    }
}
```

### 5.2 资源 (Resources)

| 资源 URI | 说明 | MIME Type |
|----------|------|-----------|
| `api://specs` | OpenAPI 规格列表 | application/json |
| `api://graph` | 知识图谱状态 | application/json |
| `api://subagents` | SubAgent 列表 | application/json |

### 5.3 提示 (Prompts)

| 提示名 | 说明 | 参数 |
|--------|------|------|
| `analyze_api` | 分析 API 用途 | api_id |
| `generate_request` | 生成请求示例 | api_id, language |

### 5.4 Tool Response 格式

```python
# query_agent 响应示例:
{
    "success": True,
    "intent": "QUERY",
    "answer": "找到以下用户相关的登录 API：",
    "apis": [
        {
            "id": "user_login",
            "path": "/api/v1/user/login",
            "method": "POST",
            "summary": "用户登录",
            "description": "验证用户名密码，返回 token",
            "parameters": [
                {"name": "username", "type": "string", "required": True},
                {"name": "password", "type": "string", "required": True}
            ],
            "response": {"token": "string"}
        }
    ],
    "subagent_used": "user_subagent",
    "suggestions": [
        "尝试调用 login 接口获取 token",
        "相关接口: logout, refresh_token"
    ],
    "metadata": {
        "query_time_ms": 1250,
        "total_apis_found": 3
    }
}
```

---

## 5.5 项目目录结构

```
agentic-api-rag-mcpserver/
├── src/
│   ├── mcp_server/           # MCP Server 实现
│   │   ├── __init__.py
│   │   ├── server.py         # MCP 服务器入口
│   │   ├── tools.py          # MCP 工具定义
│   │   ├── resources.py      # MCP 资源定义
│   │   └── prompts.py        # MCP 提示定义
│   │
│   ├── agents/               # Agent 层
│   │   ├── __init__.py
│   │   ├── manager.py        # Manager Agent (Supervisor)
│   │   ├── sub_agent.py      # SubAgent 基类
│   │   ├── intent.py         # 意图分类器
│   │   └── router.py         # 路由决策
│   │
│   ├── knowledge_graph/      # 知识图谱
│   │   ├── __init__.py
│   │   ├── graph.py         # NetworkX 图谱实现
│   │   ├── builder.py       # 图谱构建器
│   │   └── queries.py       # 图查询接口
│   │
│   ├── rag/                 # RAG 引擎
│   │   ├── __init__.py
│   │   ├── parser.py        # OpenAPI 解析器
│   │   ├── embedder.py      # 向量化
│   │   ├── retriever.py     # 检索器
│   │   └── store.py         # 向量存储 (Chroma)
│   │
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── api_spec.py      # API 规格模型
│   │   ├── graph.py         # 图谱模型
│   │   └── agent.py         # Agent 结果模型
│   │
│   └── config/             # 配置
│       ├── __init__.py
│       └── settings.py      # 配置加载
│
├── tests/                   # 测试
│   ├── test_agents/
│   ├── test_rag/
│   └── test_graph/
│
├── config/                  # 配置文件
│   └── settings.yaml
│
├── apis/                    # OpenAPI 规格文件
│   └── sample/
│
├── main.py                  # 入口文件
├── pyproject.toml
└── README.md
```

---

## 6. 实现路线

### Phase 1: 基础框架
- [ ] 项目初始化
- [ ] 目录结构搭建
- [ ] 依赖配置

### Phase 2: RAG 引擎
- [ ] OpenAPI 解析器
- [ ] 向量化模块
- [ ] Chroma 存储
- [ ] 检索器实现

### Phase 3: 知识图谱
- [ ] NetworkX 图谱
- [ ] API 实体构建
- [ ] 关系抽取
- [ ] 图查询 API

### Phase 4: Agent 层
- [ ] 意图分类器
- [ ] SubAgent 基类
- [ ] Manager Agent
- [ ] LangGraph 集成

### Phase 5: MCP 集成
- [ ] MCP Server 实现
- [ ] 工具暴露
- [ ] 资源暴露
- [ ] 端到端测试

---

## 7. 扩展性设计

### 7.1 SubAgent 扩展
```python
# 注册新的 SubAgent
manager.register_subagent(
    name="order",
    domain="order",
    subagent=OrderSubAgent(...)
)
```

### 7.2 Graph 扩展
```python
# 自定义边类型
kg.add_edge_type("validates", "验证关系")
kg.add_edge_type("returns", "返回关系")
```

### 7.3 LLM 后端切换
```python
# 切换 LLM
llm = ChatOpenAI(model="gpt-4")
# 或
llm = ChatGLM4()
```

---

## 8. 配置文件

```yaml
# config/settings.yaml
server:
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "openai"  # or "chatglm"
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"

mcp:
  server_name: "agentic-api-rag"
  version: "1.0.0"

rag:
  vector_store: "chroma"
  embedding_model: "text-embedding-ada-002"

graph:
  provider: "networkx"
  max_depth: 3

api_sources:
  - path: "./apis/openapi.json"
    tag: "internal"
  - path: "./apis/external.yaml"
    tag: "external"
```
