"""MCP tools definitions."""

from typing import Any, Dict, Optional

from src.models import AgentResponse, QueryFilters, QueryOptions


class MCPTools:
    """MCP tools for Agentic API RAG."""

    def __init__(self, manager_agent=None, simple_manager=None):
        """Initialize MCP tools."""
        self.manager_agent = manager_agent
        self.simple_manager = simple_manager

    async def query_agent(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Main entry point: Query API knowledge base with natural language."""
        # Parse filters
        query_filters = None
        if filters:
            query_filters = QueryFilters(
                tags=filters.get("tags", []),
                version=filters.get("version"),
                deprecated=filters.get("deprecated"),
                path_prefix=filters.get("path_prefix"),
                methods=filters.get("methods", []),
            )

        # Parse options
        query_options = None
        if options:
            query_options = QueryOptions(
                include_examples=options.get("include_examples", True),
                top_k=options.get("top_k", 5),
            )

        # Use manager agent if available
        if self.manager_agent:
            result: AgentResponse = await self.manager_agent.process(
                query=query,
                filters=query_filters,
                options=query_options,
            )
        elif self.simple_manager:
            result: AgentResponse = await self.simple_manager.process(
                query=query,
                filters=query_filters,
                options=query_options,
            )
        else:
            return {
                "success": False,
                "error": "No agent configured",
            }

        # Convert to dict
        return {
            "success": result.success,
            "intent": result.intent.value if result.intent else None,
            "answer": result.answer,
            "apis": result.apis,
            "subagent_used": result.subagent_used,
            "suggestions": result.suggestions,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def search_apis(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """Direct search APIs without using Agent."""
        if not self.simple_manager:
            return {
                "success": False,
                "error": "RAG engine not configured",
            }

        # Parse filters
        query_filters = None
        if filters:
            query_filters = QueryFilters(
                tags=filters.get("tags", []),
                version=filters.get("version"),
                deprecated=filters.get("deprecated"),
                path_prefix=filters.get("path_prefix"),
                methods=filters.get("methods", []),
            )

        result = await self.simple_manager.process(
            query=query,
            filters=query_filters,
            options=QueryOptions(top_k=top_k),
        )

        return {
            "success": result.success,
            "answer": result.answer,
            "apis": result.apis,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def get_api_detail(
        self,
        api_id: str,
        include_examples: bool = True,
    ) -> Dict[str, Any]:
        """Get detailed information for a specific API."""
        if not self.simple_manager:
            return {
                "success": False,
                "error": "RAG engine not configured",
            }

        # Get API from retriever
        doc = self.simple_manager.retriever.get_api_by_id(api_id)

        if not doc:
            return {
                "success": False,
                "error": f"API not found: {api_id}",
            }

        # Build response
        api_info = dict(doc.metadata)
        api_info["document"] = doc.page_content

        # Add example code if requested
        if include_examples:
            api_info["example"] = self._generate_example(api_info)

        return {
            "success": True,
            "api": api_info,
        }

    async def list_apis(
        self,
        tags: Optional[list[str]] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List all APIs or filter by tags."""
        if not self.simple_manager or not self.simple_manager.kg:
            return {
                "success": False,
                "error": "Knowledge graph not configured",
            }

        api_ids = []
        if tags:
            for tag in tags:
                ids = self.simple_manager.kg.query_by_tag(tag)
                api_ids.extend(ids)
            api_ids = list(set(api_ids))
        else:
            api_ids = self.simple_manager.kg.graph.get_all_api_ids()

        # Limit
        api_ids = api_ids[:limit]

        # Get details
        apis = []
        for api_id in api_ids:
            info = self.simple_manager.kg.graph.get_api_info(api_id)
            if info:
                apis.append(info)

        return {
            "success": True,
            "apis": apis,
            "total": len(apis),
        }

    def _generate_example(self, api_info: Dict[str, Any]) -> str:
        """Generate code example for API."""
        method = api_info.get("method", "GET").upper()
        path = api_info.get("path", "")

        example = f"```python\n"
        example += f"import requests\n\n"
        example += f"response = requests.{method.lower()}(\n"
        example += f'    "{path}",\n'
        example += f'    headers={{"Authorization": "Bearer <token>"}}\n'
        example += f")\n"
        example += f"```\n"

        return example


def get_tool_definitions() -> list[Dict[str, Any]]:
    """Get MCP tool definitions."""
    return [
        {
            "name": "query_agent",
            "description": "Main entry point: Query API knowledge base with natural language. Use this for most queries about APIs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query, e.g., '查一下用户登录接口'",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filter conditions",
                        "properties": {
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by tags",
                            },
                            "version": {
                                "type": "string",
                                "description": "API version",
                            },
                            "deprecated": {
                                "type": "boolean",
                                "description": "Filter by deprecated status",
                            },
                            "path_prefix": {
                                "type": "string",
                                "description": "Path prefix filter",
                            },
                            "methods": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "HTTP methods filter",
                            },
                        },
                    },
                    "options": {
                        "type": "object",
                        "description": "Additional options",
                        "properties": {
                            "include_examples": {
                                "type": "boolean",
                                "description": "Include code examples",
                                "default": True,
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results",
                                "default": 5,
                            },
                        },
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "search_apis",
            "description": "Direct search APIs without using Agent. Faster but less intelligent than query_agent.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filter conditions",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_api_detail",
            "description": "Get detailed information for a specific API by ID.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "api_id": {
                        "type": "string",
                        "description": "API unique identifier, e.g., 'login'",
                    },
                    "include_examples": {
                        "type": "boolean",
                        "description": "Include code examples",
                        "default": True,
                    },
                },
                "required": ["api_id"],
            },
        },
        {
            "name": "list_apis",
            "description": "List all APIs or filter by tags.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50,
                    },
                },
            },
        },
    ]
