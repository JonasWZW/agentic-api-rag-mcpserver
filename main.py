"""Main entry point for Agentic API RAG MCP Server."""

import asyncio
import sys
from pathlib import Path

from src.config import Settings, settings
from src.knowledge_graph import APIGraph, GraphBuilder
from src.mcp_server.server import AgenticAPIRAGServer
from src.rag import Embedder, OpenAPIParser, VectorStore


async def main():
    """Main function."""
    # Load configuration
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    if config_path.exists():
        config = Settings.from_yaml(str(config_path))
    else:
        config = settings

    # Get OpenAPI spec paths
    spec_paths = []
    apis_dir = Path(__file__).parent / "apis"
    if apis_dir.exists():
        for spec_file in apis_dir.rglob("*.yaml"):
            spec_paths.append(str(spec_file))
        for spec_file in apis_dir.rglob("*.json"):
            spec_paths.append(str(spec_file))

    # Override with command line args if provided
    if len(sys.argv) > 1:
        spec_paths = sys.argv[1:]

    # Initialize server
    server = AgenticAPIRAGServer(config)

    print(f"Initializing with {len(spec_paths)} OpenAPI specs...")

    # Initialize with specs
    server.initialize(
        openapi_specs=spec_paths,
        api_key=config.llm.api_key,
    )

    print(f"Loaded {len(server._apis)} APIs")
    print(f"Graph nodes: {server.knowledge_graph.graph.number_of_nodes()}")
    print(f"Graph edges: {server.knowledge_graph.graph.number_of_edges()}")

    # Run server
    print("Starting MCP server...")
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
