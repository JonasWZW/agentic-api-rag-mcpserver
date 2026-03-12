"""MCP resources definitions."""


def get_resource_definitions() -> list[dict]:
    """Get MCP resource definitions."""
    return [
        {
            "uri": "api://specs",
            "name": "API Specifications",
            "description": "List of loaded OpenAPI specifications",
            "mimeType": "application/json",
        },
        {
            "uri": "api://graph",
            "name": "Knowledge Graph Status",
            "description": "Current status of the API knowledge graph",
            "mimeType": "application/json",
        },
        {
            "uri": "api://subagents",
            "name": "SubAgent List",
            "description": "List of available SubAgents",
            "mimeType": "application/json",
        },
    ]


class MCPResources:
    """MCP resources provider."""

    def __init__(self, manager_agent=None, simple_manager=None):
        """Initialize MCP resources."""
        self.manager_agent = manager_agent
        self.simple_manager = simple_manager

    async def get_specs(self) -> dict:
        """Get API specs info."""
        if not self.simple_manager:
            return {"specs": [], "count": 0}

        # This would need to track loaded specs
        return {
            "specs": [],
            "count": 0,
            "message": "Use load_spec tool to add OpenAPI specifications",
        }

    async def get_graph_status(self) -> dict:
        """Get knowledge graph status."""
        if not self.simple_manager or not self.simple_manager.kg:
            return {
                "status": "not_initialized",
                "nodes": 0,
                "edges": 0,
            }

        stats = self.simple_manager.kg.get_stats()

        return {
            "status": "ready",
            "nodes": stats.total_nodes,
            "edges": stats.total_edges,
            "node_types": stats.node_types,
            "edge_types": stats.edge_types,
        }

    async def get_subagents(self) -> dict:
        """Get SubAgent list."""
        if not self.manager_agent:
            return {"subagents": [], "count": 0}

        subagents = []
        for name, agent in self.manager_agent.sub_agents.items():
            subagents.append({
                "name": name,
                "domain": agent.domain,
                "tags": agent.tags,
                "api_count": len(agent._api_cache),
            })

        return {
            "subagents": subagents,
            "count": len(subagents),
        }
