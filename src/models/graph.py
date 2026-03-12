"""Graph models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.models.api_spec import EdgeType, GraphEdge, GraphNode, NodeType


@dataclass
class GraphQuery:
    """Graph query."""

    query: str
    depth: int = 2
    node_type: Optional[NodeType] = None
    edge_type: Optional[EdgeType] = None


@dataclass
class GraphStats:
    """Graph statistics."""

    total_nodes: int
    total_edges: int
    node_types: Dict[str, int] = field(default_factory=dict)
    edge_types: Dict[str, int] = field(default_factory=dict)
