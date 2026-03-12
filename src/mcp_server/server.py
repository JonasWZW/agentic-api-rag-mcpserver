"""MCP Server implementation."""

import asyncio
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, Resource, Prompt

from src.agents import ManagerAgent, SimpleManagerAgent
from src.config import Settings, settings
from src.knowledge_graph import APIGraph, GraphBuilder, GraphQuerier
from src.mcp_server.prompts import MCPPrompts, get_prompt_definitions
from src.mcp_server.resources import MCPResources, get_resource_definitions
from src.mcp_server.tools import MCPTools, get_tool_definitions
from src.models import APIEntity
from src.rag import Embedder, OpenAPIParser, Retriever, VectorStore


class AgenticAPIRAGServer:
    """MCP Server for Agentic API RAG."""

    def __init__(self, config: Optional[Settings] = None):
        """Initialize the server."""
        self.config = config or settings
        self.server = Server(
            {
                "name": self.config.mcp.server_name,
                "version": self.config.mcp.version,
            }
        )

        # Components
        self.embedder: Optional[Embedder] = None
        self.vector_store: Optional[VectorStore] = None
        self.retriever: Optional[Retriever] = None
        self.knowledge_graph: Optional[APIGraph] = None
        self.graph_querier: Optional[GraphQuerier] = None
        self.manager_agent: Optional[ManagerAgent] = None
        self.simple_manager: Optional[SimpleManagerAgent] = None
        self.parser = OpenAPIParser()

        # MCP components
        self.tools: Optional[MCPTools] = None
        self.resources: Optional[MCPResources] = None
        self.prompts: Optional[MCPPrompts] = None

        # API entities
        self._apis: list[APIEntity] = []

        # Setup handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP server handlers."""
        # List tools
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            tool_defs = get_tool_definitions()
            return [
                Tool(
                    name=tool["name"],
                    description=tool["description"],
                    inputSchema=tool["input_schema"],
                )
                for tool in tool_defs
            ]

        # Call tool
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> Any:
            return await self._handle_tool(name, arguments)

        # List resources
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            resource_defs = get_resource_definitions()
            return [
                Resource(
                    uri=res["uri"],
                    name=res["name"],
                    description=res["description"],
                    mimeType=res["mimeType"],
                )
                for res in resource_defs
            ]

        # Read resource
        @self.server.read_resource()
        async def read_resource(uri: str) -> Any:
            return await self._handle_resource(uri)

        # List prompts
        @self.server.list_prompts()
        async def list_prompts() -> list[Prompt]:
            prompt_defs = get_prompt_definitions()
            return [
                Prompt(
                    name=prompt["name"],
                    description=prompt["description"],
                    arguments=[
                        Prompt.Argument(
                            name=arg["name"],
                            description=arg["description"],
                            required=arg.get("required", False),
                        )
                        for arg in prompt.get("arguments", [])
                    ],
                )
                for prompt in prompt_defs
            ]

        # Get prompt
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict) -> Any:
            return await self._handle_prompt(name, arguments)

    async def _handle_tool(self, name: str, arguments: dict) -> Any:
        """Handle tool call."""
        if not self.tools:
            return {"error": "Server not initialized"}

        if name == "query_agent":
            return await self.tools.query_agent(
                query=arguments.get("query"),
                filters=arguments.get("filters"),
                options=arguments.get("options"),
            )
        elif name == "search_apis":
            return await self.tools.search_apis(
                query=arguments.get("query"),
                filters=arguments.get("filters"),
                top_k=arguments.get("top_k", 10),
            )
        elif name == "get_api_detail":
            return await self.tools.get_api_detail(
                api_id=arguments.get("api_id"),
                include_examples=arguments.get("include_examples", True),
            )
        elif name == "list_apis":
            return await self.tools.list_apis(
                tags=arguments.get("tags"),
                limit=arguments.get("limit", 50),
            )
        else:
            return {"error": f"Unknown tool: {name}"}

    async def _handle_resource(self, uri: str) -> Any:
        """Handle resource request."""
        if not self.resources:
            return {"error": "Server not initialized"}

        if uri == "api://specs":
            return await self.resources.get_specs()
        elif uri == "api://graph":
            return await self.resources.get_graph_status()
        elif uri == "api://subagents":
            return await self.resources.get_subagents()
        else:
            return {"error": f"Unknown resource: {uri}"}

    async def _handle_prompt(self, name: str, arguments: dict) -> Any:
        """Handle prompt request."""
        if not self.prompts:
            return {"error": "Server not initialized"}

        if name == "analyze_api":
            return await self.prompts.analyze_api(arguments.get("api_id"))
        elif name == "generate_request":
            return await self.prompts.generate_request(
                arguments.get("api_id"),
                arguments.get("language", "python"),
            )
        else:
            return {"error": f"Unknown prompt: {name}"}

    def initialize(
        self,
        openapi_specs: Optional[list[str]] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize the server with OpenAPI specs."""
        # Initialize embedder
        self.embedder = Embedder(
            model=self.config.rag.embedding_model,
            api_key=api_key or self.config.llm.api_key,
            base_url=self.config.llm.base_url,
        )

        # Initialize vector store
        self.vector_store = VectorStore(
            persist_directory="./data/vectorstore",
            collection_name="api_docs",
            embedder=self.embedder,
        )

        # Initialize knowledge graph
        self.knowledge_graph = APIGraph()

        # Parse and load OpenAPI specs
        if openapi_specs:
            for spec_path in openapi_specs:
                apis = self.parser.parse_file(spec_path)
                self._apis.extend(apis)

                # Add to graph
                for api in apis:
                    self.knowledge_graph.add_api(api)

                # Add to vector store
                if self.vector_store:
                    self.vector_store.add_api_documents(apis)

        # Initialize retriever
        self.retriever = Retriever(self.vector_store)

        # Initialize graph querier
        self.graph_querier = GraphQuerier(self.knowledge_graph)

        # Initialize simple manager
        self.simple_manager = SimpleManagerAgent(
            retriever=self.retriever,
            knowledge_graph=self.graph_querier,
        )

        # Initialize MCP components
        self.tools = MCPTools(simple_manager=self.simple_manager)
        self.resources = MCPResources(simple_manager=self.simple_manager)
        self.prompts = MCPPrompts(simple_manager=self.simple_manager)

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main():
    """Main entry point."""
    import sys

    # Get OpenAPI spec paths from args
    spec_paths = []
    if len(sys.argv) > 1:
        spec_paths = sys.argv[1:]

    # Create and initialize server
    server = AgenticAPIRAGServer()
    server.initialize(openapi_specs=spec_paths or None)

    # Run server
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
