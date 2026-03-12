"""Knowledge graph using NetworkX."""

from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from src.models import APIEntity, EdgeType, GraphEdge, GraphNode, GraphStats, NodeType


class APIGraph:
    """Knowledge graph for API relationships using NetworkX."""

    def __init__(self):
        """Initialize the graph."""
        self.graph = nx.MultiDiGraph()
        self._api_nodes: Dict[str, APIEntity] = {}

    def add_api(self, api: APIEntity) -> None:
        """Add an API node to the graph."""
        # Add API node
        self.graph.add_node(
            api.id,
            type=NodeType.API.value,
            id=api.id,
            path=api.path,
            method=api.method.value,
            summary=api.summary,
            tags=",".join(api.tags),
        )
        self._api_nodes[api.id] = api

        # Add tag nodes and edges
        for tag in api.tags:
            tag_id = f"tag_{tag}"
            if not self.graph.has_node(tag_id):
                self.graph.add_node(tag_id, type=NodeType.TAG.value, name=tag)
            self.graph.add_edge(
                api.id,
                tag_id,
                type=EdgeType.HAS_TAG.value,
                weight=1.0,
            )

        # Add parameter nodes
        for param in api.parameters:
            param_id = f"{api.id}_param_{param.name}"
            self.graph.add_node(
                param_id,
                type=NodeType.PARAMETER.value,
                name=param.name,
                param_type=param.type,
                required=param.required,
            )
            self.graph.add_edge(
                api.id,
                param_id,
                type=EdgeType.HAS_PARAM.value,
                weight=0.8,
            )

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self.graph.add_edge(
            edge.source,
            edge.target,
            type=edge.type.value,
            weight=edge.weight,
            reason=edge.reason,
        )

    def find_related(
        self,
        api_id: str,
        depth: int = 2,
        edge_types: Optional[List[EdgeType]] = None,
    ) -> List[str]:
        """Find related API IDs."""
        if not self.graph.has_node(api_id):
            return []

        related = set()

        # BFS traversal
        current_level = {api_id}
        visited = {api_id}

        for _ in range(depth):
            next_level = set()
            for node in current_level:
                # Get neighbors
                neighbors = self.graph.neighbors(node)
                for neighbor in neighbors:
                    if neighbor not in visited:
                        # Check edge type filter
                        if edge_types:
                            edge_data = self.graph.get_edge_data(node, neighbor)
                            if edge_data:
                                edge_type = edge_data.get("type")
                                if edge_type not in [et.value for et in edge_types]:
                                    continue

                        next_level.add(neighbor)
                        visited.add(neighbor)

                        # If it's an API node, add to results
                        if self.graph.nodes[neighbor].get("type") == NodeType.API.value:
                            related.add(neighbor)

            current_level = next_level
            if not current_level:
                break

        return list(related)

    def find_by_tag(self, tag: str) -> List[str]:
        """Find all APIs with a specific tag."""
        tag_id = f"tag_{tag}"
        if not self.graph.has_node(tag_id):
            return []

        # Get all APIs that have this tag
        apis = []
        for node in self.graph.predecessors(tag_id):
            node_data = self.graph.nodes[node]
            if node_data.get("type") == NodeType.API.value:
                apis.append(node)

        return apis

    def find_dependencies(self, api_id: str) -> List[str]:
        """Find APIs that this API depends on."""
        if not self.graph.has_node(api_id):
            return []

        deps = []
        for target in self.graph.successors(api_id):
            edge_data = self.graph.get_edge_data(api_id, target)
            if edge_data:
                for ed in edge_data.values():
                    if ed.get("type") == EdgeType.DEPENDS_ON.value:
                        deps.append(target)

        return deps

    def find_similar(self, api_id: str) -> List[Tuple[str, float]]:
        """Find similar APIs based on graph structure."""
        if not self.graph.has_node(api_id):
            return []

        # Get Jaccard similarity based on neighbors
        api_neighbors = set(self.graph.neighbors(api_id))
        if not api_neighbors:
            return []

        similarities = []
        for node in self.graph.nodes():
            if node == api_id:
                continue

            node_data = self.graph.nodes[node]
            if node_data.get("type") != NodeType.API.value:
                continue

            node_neighbors = set(self.graph.neighbors(node))
            intersection = api_neighbors & node_neighbors
            union = api_neighbors | node_neighbors

            if union:
                similarity = len(intersection) / len(union)
                similarities.append((node, similarity))

        return sorted(similarities, key=lambda x: x[1], reverse=True)

    def get_api_info(self, api_id: str) -> Optional[Dict[str, Any]]:
        """Get API information from graph."""
        if not self.graph.has_node(api_id):
            return None

        return dict(self.graph.nodes[api_id])

    def get_stats(self) -> GraphStats:
        """Get graph statistics."""
        node_types: Dict[str, int] = {}
        edge_types: Dict[str, int] = {}

        for _, data in self.graph.nodes(data=True):
            node_type = data.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1

        for _, _, data in self.graph.edges(data=True):
            edge_type = data.get("type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

        return GraphStats(
            total_nodes=self.graph.number_of_nodes(),
            total_edges=self.graph.number_of_edges(),
            node_types=node_types,
            edge_types=edge_types,
        )

    def get_all_api_ids(self) -> List[str]:
        """Get all API IDs."""
        apis = []
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == NodeType.API.value:
                apis.append(node)
        return apis

    def has_api(self, api_id: str) -> bool:
        """Check if API exists in graph."""
        return api_id in self._api_nodes

    def remove_api(self, api_id: str) -> None:
        """Remove API from graph."""
        if api_id in self._api_nodes:
            self.graph.remove_node(api_id)
            del self._api_nodes[api_id]

    def clear(self) -> None:
        """Clear the graph."""
        self.graph.clear()
        self._api_nodes.clear()
