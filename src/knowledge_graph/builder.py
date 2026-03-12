"""Graph builder for constructing API knowledge graph."""

import re
from typing import List

from src.models import APIEntity, APIGraph, EdgeType
from src.rag.parser import OpenAPIParser


class GraphBuilder:
    """Build knowledge graph from API entities."""

    def __init__(self, graph: APIGraph):
        """Initialize builder."""
        self.graph = graph
        self.parser = OpenAPIParser()

    def build_from_apis(self, apis: List[APIEntity]) -> None:
        """Build graph from API entities."""
        # Add all APIs as nodes
        for api in apis:
            self.graph.add_api(api)

        # Build relationships between APIs
        self._build_relationships(apis)

    def build_from_specs(self, spec_paths: List[str]) -> None:
        """Build graph from OpenAPI spec files."""
        apis = []
        for spec_path in spec_paths:
            parsed_apis = self.parser.parse_file(spec_path)
            apis.extend(parsed_apis)

        self.build_from_apis(apis)

    def _build_relationships(self, apis: List[APIEntity]) -> None:
        """Build relationships between APIs."""
        # Index APIs by tags
        apis_by_tag: dict = {}
        for api in apis:
            for tag in api.tags:
                if tag not in apis_by_tag:
                    apis_by_tag[tag] = []
                apis_by_tag[tag].append(api)

        # Build relationships
        for api in apis:
            # Similar operations (same method, similar path)
            self._build_similar_ops(api, apis)

            # API dependencies based on path patterns
            self._build_path_dependencies(api, apis)

    def _build_similar_ops(self, api: APIEntity, all_apis: List[APIEntity]) -> None:
        """Build edges for similar operations."""
        for other in all_apis:
            if other.id == api.id:
                continue

            # Same HTTP method
            if other.method == api.method:
                # Similar path (e.g., /users and /users/{id})
                if self._is_similar_path(api.path, other.path):
                    self.graph.add_edge(
                        source=api.id,
                        target=other.id,
                        type=EdgeType.SIMILAR_TO,
                        weight=0.6,
                    )

                # Same operation type (e.g., create_* and list_*)
                if self._has_same_operation_type(api.id, other.id):
                    self.graph.add_edge(
                        source=api.id,
                        target=other.id,
                        type=EdgeType.SAME_OP,
                        weight=0.5,
                    )

    def _build_path_dependencies(self, api: APIEntity, all_apis: List[APIEntity]) -> None:
        """Build dependency edges based on path hierarchy."""
        # Check if api.path is a subpath of other.paths (e.g., /users depends on /users/{id})
        api_base = self._get_path_base(api.path)

        for other in all_apis:
            if other.id == api.id:
                continue

            other_base = self._get_path_base(other.path)

            # If this API is a detail endpoint, it may depend on list endpoint
            if api_base == other_base:
                # Check if one is parent of other
                if api.path.count("/") < other.path.count("/"):
                    # api is parent, no dependency
                    pass
                elif api.path.count("/") > other.path.count("/"):
                    # api is child, depends on parent
                    self.graph.add_edge(
                        source=api.id,
                        target=other.id,
                        type=EdgeType.DEPENDS_ON,
                        weight=0.3,
                        reason="Parent-child relationship",
                    )

    def _is_similar_path(self, path1: str, path2: str) -> bool:
        """Check if two paths are similar."""
        # Normalize paths
        p1 = re.sub(r"\{[^}]+\}", "{id}", path1)
        p2 = re.sub(r"\{[^}]+\}", "{id}", path2)

        return p1 == p2 and path1 != path2

    def _has_same_operation_type(self, id1: str, id2: str) -> bool:
        """Check if two API IDs have the same operation type."""
        # Extract operation prefix (e.g., "create", "list", "get")
        op1 = id1.split("_")[0] if "_" in id1 else ""
        op2 = id2.split("_")[0] if "_" in id2 else ""

        return op1 and op2 and op1 == op2

    def _get_path_base(self, path: str) -> str:
        """Get base path without parameters."""
        # Remove path parameters
        base = re.sub(r"\{[^}]+\}", "", path)
        # Remove trailing slashes
        base = base.rstrip("/")
        return base
