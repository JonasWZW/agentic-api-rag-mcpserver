"""SubAgent for handling domain-specific API queries."""

from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel

from src.models import APIEntity, Intent, IntentResult, QueryFilters, QueryOptions, SubAgentResult
from src.rag.retriever import Retriever


class SubAgent:
    """SubAgent for handling domain-specific API queries."""

    def __init__(
        self,
        name: str,
        domain: str,
        tags: List[str],
        llm: Optional[BaseChatModel] = None,
        retriever: Optional[Retriever] = None,
    ):
        """Initialize SubAgent."""
        self.name = name
        self.domain = domain
        self.tags = tags
        self.llm = llm
        self.retriever = retriever
        self._api_cache: Dict[str, APIEntity] = {}

    def register_apis(self, apis: List[APIEntity]) -> None:
        """Register APIs for this agent."""
        for api in apis:
            if any(tag in api.tags for tag in self.tags):
                self._api_cache[api.id] = api

    async def execute(
        self,
        query: str,
        intent: Intent,
        filters: Optional[QueryFilters] = None,
        context: Optional[List[str]] = None,
    ) -> SubAgentResult:
        """Execute query and return results."""
        # Merge filters
        merged_filters = self._merge_filters(filters)

        # Build search query
        search_query = self._build_search_query(query)

        # Retrieve APIs
        retrieval_results = []
        if self.retriever:
            retrieval_results = self.retriever.search(
                query=search_query,
                filters=merged_filters,
                top_k=5,
            )

        # Get API details
        apis = []
        for result in retrieval_results:
            if result.api_id in self._api_cache:
                api = self._api_cache[result.api_id]
                apis.append(api.to_dict())

        # Generate answer based on intent
        answer = await self._generate_answer(query, intent, apis)

        # Generate suggestions
        suggestions = self._generate_suggestions(query, intent, apis)

        return SubAgentResult(
            answer=answer,
            apis=apis,
            subagent_name=self.name,
            intent=intent,
            suggestions=suggestions,
        )

    def _merge_filters(self, filters: Optional[QueryFilters]) -> QueryFilters:
        """Merge agent-specific filters with query filters."""
        merged = QueryFilters()

        # Start with agent's domain tags
        merged.tags = list(self.tags)

        # Add query filters
        if filters:
            if filters.tags:
                merged.tags.extend(filters.tags)
            if filters.version:
                merged.version = filters.version
            if filters.deprecated is not None:
                merged.deprecated = filters.deprecated
            if filters.path_prefix:
                merged.path_prefix = filters.path_prefix
            if filters.methods:
                merged.methods = filters.methods

        # Deduplicate tags
        merged.tags = list(set(merged.tags))

        return merged

    def _build_search_query(self, query: str) -> str:
        """Build search query with domain context."""
        # Add domain prefix if not already present
        if not any(tag in query.lower() for tag in self.tags):
            return f"{self.domain} {query}"
        return query

    async def _generate_answer(
        self,
        query: str,
        intent: Intent,
        apis: List[Dict[str, Any]],
    ) -> str:
        """Generate answer based on intent."""
        if not apis:
            return f"未找到与 {query} 相关的 API"

        if intent == Intent.QUERY:
            return self._generate_query_answer(query, apis)
        elif intent == Intent.UNDERSTAND:
            return self._generate_understand_answer(query, apis)
        elif intent == Intent.COMPARE:
            return self._generate_compare_answer(query, apis)
        elif intent == Intent.RECOMMEND:
            return self._generate_recommend_answer(query, apis)
        elif intent == Intent.DEBUG:
            return self._generate_debug_answer(query, apis)
        elif intent == Intent.CALL:
            return self._generate_call_answer(query, apis)
        else:
            return self._generate_query_answer(query, apis)

    def _generate_query_answer(self, query: str, apis: List[Dict[str, Any]]) -> str:
        """Generate answer for QUERY intent."""
        lines = [f"找到 {len(apis)} 个相关 API：\n"]

        for api in apis:
            method = api.get("method", "GET").upper()
            path = api.get("path", "")
            summary = api.get("summary", "")
            lines.append(f"- **{method}** `{path}` - {summary}")

        return "\n".join(lines)

    def _generate_understand_answer(self, query: str, apis: List[Dict[str, Any]]) -> str:
        """Generate answer for UNDERSTAND intent."""
        if not apis:
            return "未找到相关 API"

        api = apis[0]
        lines = [f"API 详情：\n"]

        method = api.get("method", "GET").upper()
        path = api.get("path", "")
        summary = api.get("summary", "")
        description = api.get("description", "")

        lines.append(f"- **接口**: {method} `{path}`")
        lines.append(f"- **描述**: {summary}")
        if description:
            lines.append(f"- **说明**: {description}")

        # Add parameters
        params = api.get("parameters", [])
        if params:
            lines.append("\n**参数**:")
            for p in params:
                required = "必需" if p.get("required") else "可选"
                lines.append(f"- `{p['name']}` ({p['type']}) - {required}")

        return "\n".join(lines)

    def _generate_compare_answer(self, query: str, apis: List[Dict[str, Any]]) -> str:
        """Generate answer for COMPARE intent."""
        if len(apis) < 2:
            return "需要至少 2 个 API 才能进行比较"

        lines = ["API 比较：\n"]

        for i, api in enumerate(apis, 1):
            method = api.get("method", "GET").upper()
            path = api.get("path", "")
            lines.append(f"### {i}. {method} `{path}`")
            lines.append(f"   {api.get('summary', '')}")
            lines.append("")

        return "\n".join(lines)

    def _generate_recommend_answer(self, query: str, apis: List[Dict[str, Any]]) -> str:
        """Generate answer for RECOMMEND intent."""
        if not apis:
            return "未找到相关 API"

        lines = ["推荐以下 API：\n"]

        for api in apis:
            method = api.get("method", "GET").upper()
            path = api.get("path", "")
            summary = api.get("summary", "")
            lines.append(f"- **{method}** `{path}`")
            lines.append(f"  {summary}")

        return "\n".join(lines)

    def _generate_debug_answer(self, query: str, apis: List[Dict[str, Any]]) -> str:
        """Generate answer for DEBUG intent."""
        lines = ["调试建议：\n"]

        for api in apis:
            method = api.get("method", "GET").upper()
            path = api.get("path", "")
            lines.append(f"- 检查 **{method}** `{path}`")
            lines.append(f"  确保参数正确")

        lines.append("\n常见问题：")
        lines.append("- 检查认证信息是否正确")
        lines.append("- 验证请求参数格式")
        lines.append("- 确认 API 版本")

        return "\n".join(lines)

    def _generate_call_answer(self, query: str, apis: List[Dict[str, Any]]) -> str:
        """Generate answer for CALL intent."""
        if not apis:
            return "未找到可调用的 API"

        api = apis[0]
        method = api.get("method", "GET").upper()
        path = api.get("path", "")

        lines = [f"调用建议：\n"]
        lines.append(f"**请求**: {method} `{path}`")

        # Add example
        lines.append("\n**调用示例**:")
        lines.append(f"```python")
        lines.append(f"import requests")
        lines.append(f"")
        lines.append(f"response = requests.{method.lower()}(  # 或 httpx")
        lines.append(f'    "{path}",')
        lines.append(f'    headers={{"Authorization": "Bearer <token>"}}')
        lines.append(f")")
        lines.append(f"```")

        return "\n".join(lines)

    def _generate_suggestions(
        self,
        query: str,
        intent: Intent,
        apis: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate suggestions based on retrieved APIs."""
        suggestions = []

        if intent in [Intent.QUERY, Intent.RECOMMEND] and apis:
            # Suggest related APIs
            if len(apis) > 1:
                suggestions.append(f"可以尝试调用 {apis[0].get('method', 'GET').upper()} {apis[0].get('path', '')}")

        if intent == Intent.CALL:
            suggestions.append("注意先获取认证 token")
            suggestions.append("检查参数必填项")

        return suggestions

    def as_tool(self):
        """Convert to LangChain Tool."""
        from langchain_core.tools import Tool

        return Tool(
            name=self.name,
            description=f"处理 {self.domain} 领域的 API 查询",
            func=self._sync_execute,
        )

    def _sync_execute(self, query: str) -> str:
        """Synchronous execute for LangChain Tool."""
        import asyncio

        return asyncio.run(self.execute(query, Intent.QUERY))
