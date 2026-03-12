"""Manager Agent for orchestrating SubAgents."""

import time
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel

from src.agents.intent import IntentClassifier, extract_filters_from_query
from src.agents.router import Router
from src.agents.sub_agent import SubAgent
from src.knowledge_graph.queries import GraphQuerier
from src.models import (
    AgentResponse,
    APIEntity,
    Intent,
    IntentResult,
    QueryFilters,
    QueryOptions,
    SubAgentResult,
)
from src.rag.retriever import Retriever


class ManagerAgent:
    """Manager Agent - orchestrates SubAgents for API queries."""

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        sub_agents: Optional[List[SubAgent]] = None,
        knowledge_graph: Optional[GraphQuerier] = None,
        retriever: Optional[Retriever] = None,
        apis: Optional[List[APIEntity]] = None,
    ):
        """Initialize Manager Agent."""
        self.llm = llm
        self.intent_classifier = IntentClassifier(llm)

        # Setup sub-agents
        self.sub_agents: Dict[str, SubAgent] = {}
        if sub_agents:
            for agent in sub_agents:
                self.sub_agents[agent.name] = agent

        # Register APIs to sub-agents
        if apis:
            self._register_apis(apis)

        # Setup router
        agent_configs = {
            name: {"domain": agent.domain, "tags": agent.tags}
            for name, agent in self.sub_agents.items()
        }
        self.router = Router(agent_configs)

        # Knowledge graph
        self.kg = knowledge_graph
        self.retriever = retriever

    def register_subagent(self, agent: SubAgent) -> None:
        """Register a SubAgent."""
        self.sub_agents[agent.name] = agent
        # Update router
        agent_configs = {
            name: {"domain": agent.domain, "tags": agent.tags}
            for name, agent in self.sub_agents.items()
        }
        self.router = Router(agent_configs)

    def _register_apis(self, apis: List[APIEntity]) -> None:
        """Register APIs to all sub-agents."""
        for agent in self.sub_agents.values():
            agent.register_apis(apis)

    async def process(
        self,
        query: str,
        filters: Optional[QueryFilters] = None,
        options: Optional[QueryOptions] = None,
    ) -> AgentResponse:
        """Process user query."""
        start_time = time.time()

        try:
            # Step 1: Intent classification
            intent_result = await self.intent_classifier.classify(query)

            # Step 2: Extract filters from query if not provided
            if not filters:
                filters = extract_filters_from_query(query)

            # Step 3: Knowledge graph query for context
            context_apis = []
            if self.kg:
                context_api_ids = self.kg.query_related_apis(query, filters)
                context_apis = context_api_ids

            # Step 4: Route to sub-agents
            route = self.router.route(intent_result, filters)

            # Step 5: Execute sub-agents
            sub_results = []
            if route.target_subagents:
                for agent_name in route.target_subagents:
                    agent = self.sub_agents.get(agent_name)
                    if agent:
                        result = await agent.execute(
                            query=query,
                            intent=intent_result.intent,
                            filters=filters,
                            context=context_apis,
                        )
                        sub_results.append(result)

            # Step 6: Aggregate results
            aggregated = self._aggregate_results(sub_results, intent_result)

            # Add metadata
            elapsed_ms = int((time.time() - start_time) * 1000)
            aggregated.metadata = {
                "query_time_ms": elapsed_ms,
                "total_apis_found": len(aggregated.apis),
                "subagents_used": route.target_subagents,
            }

            return aggregated

        except Exception as e:
            return AgentResponse(
                success=False,
                answer=f"处理查询时出错: {str(e)}",
                error=str(e),
                metadata={"query_time_ms": int((time.time() - start_time) * 1000)},
            )

    def _aggregate_results(
        self,
        sub_results: List[SubAgentResult],
        intent_result: IntentResult,
    ) -> AgentResponse:
        """Aggregate results from multiple sub-agents."""
        if not sub_results:
            return AgentResponse(
                success=True,
                intent=intent_result.intent,
                answer="未找到相关 API",
            )

        # Merge answers
        answers = [r.answer for r in sub_results if r.answer]
        answer = "\n\n".join(answers)

        # Merge APIs (deduplicate)
        seen_ids = set()
        merged_apis = []
        for r in sub_results:
            for api in r.apis:
                api_id = api.get("id")
                if api_id and api_id not in seen_ids:
                    seen_ids.add(api_id)
                    merged_apis.append(api)

        # Merge suggestions
        suggestions = []
        for r in sub_results:
            suggestions.extend(r.suggestions)
        suggestions = list(set(suggestions))

        # Get subagent used
        subagent_used = sub_results[0].subagent_name if sub_results else None

        return AgentResponse(
            success=True,
            intent=intent_result.intent,
            answer=answer,
            apis=merged_apis,
            subagent_used=subagent_used,
            suggestions=suggestions,
        )


class SimpleManagerAgent:
    """Simple Manager Agent for direct RAG queries without LLM."""

    def __init__(
        self,
        retriever: Retriever,
        knowledge_graph: Optional[GraphQuerier] = None,
    ):
        """Initialize simple manager."""
        self.retriever = retriever
        self.kg = knowledge_graph

    async def process(
        self,
        query: str,
        filters: Optional[QueryFilters] = None,
        options: Optional[QueryOptions] = None,
    ) -> AgentResponse:
        """Process query without LLM."""
        start_time = time.time()

        try:
            # Extract filters
            if not filters:
                filters = extract_filters_from_query(query)

            # Set defaults
            top_k = options.top_k if options else 5

            # Search RAG
            rag_results = self.retriever.search(query, filters, top_k)

            # Get API details
            apis = []
            for result in rag_results:
                doc = self.retriever.get_api_by_id(result.api_id)
                if doc:
                    # Extract metadata
                    api_dict = dict(doc.metadata)
                    api_dict["document"] = doc.page_content
                    apis.append(api_dict)

            # Generate answer
            if apis:
                answer = f"找到 {len(apis)} 个相关 API:\n"
                for api in apis:
                    answer += f"- {api.get('method', '?').upper()} {api.get('path', '')}\n"
            else:
                answer = "未找到相关 API"

            elapsed_ms = int((time.time() - start_time) * 1000)

            return AgentResponse(
                success=True,
                answer=answer,
                apis=apis,
                metadata={
                    "query_time_ms": elapsed_ms,
                    "total_apis_found": len(apis),
                },
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                answer=f"处理查询时出错: {str(e)}",
                error=str(e),
                metadata={"query_time_ms": int((time.time() - start_time) * 1000)},
            )
