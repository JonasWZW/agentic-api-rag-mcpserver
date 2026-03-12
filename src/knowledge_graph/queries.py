"""Graph query interface."""

from typing import Any, Dict, List, Optional, Tuple

from src.models import APIEntity, APIGraph, EdgeType, GraphStats, QueryFilters


class GraphQuerier:
    """Query interface for API knowledge graph."""

    def __init__(self, graph: APIGraph):
        """Initialize querier."""
        self.graph = graph

    def query_related_apis(
        self,
        query: str,
        filters: Optional[QueryFilters] = None,
        depth: int = 2,
    ) -> List[str]:
        """Query for related APIs based on query text."""
        # Extract keywords from query
        keywords = self._extract_keywords(query)

        # Find APIs matching keywords
        matching_apis = set()

        for keyword in keywords:
            # Search by tag
            if filters and filters.tags:
                for tag in filters.tags:
                    apis = self.graph.find_by_tag(tag)
                    matching_apis.update(apis)
            else:
                # Search all tags that match keyword
                apis = self.graph.find_by_tag(keyword)
                matching_apis.update(apis)

        # Expand to related APIs
        related_apis = set()
        for api_id in matching_apis:
            related = self.graph.find_related(api_id, depth=depth)
            related_api_ids = [
                rid for rid in related
                if self.graph.graph.nodes[rid].get("type") == "API"
            ]
            related_apis.update(related_api_ids)

        # Apply additional filters
        if filters:
            result = []
            for api_id in related_apis:
                api_info = self.graph.get_api_info(api_id)
                if self._matches_filters(api_info, filters):
                    result.append(api_id)
            return result

        return list(related_apis)

    def query_by_tag(self, tag: str) -> List[str]:
        """Query APIs by tag."""
        return self.graph.find_by_tag(tag)

    def query_dependencies(self, api_id: str) -> List[str]:
        """Query dependencies for an API."""
        return self.graph.find_dependencies(api_id)

    def query_similar(self, api_id: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Query similar APIs."""
        return self.graph.find_similar(api_id)[:limit]

    def get_api_context(self, api_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get context for an API including related APIs."""
        api_info = self.graph.get_api_info(api_id)
        if not api_info:
            return {}

        related = self.graph.find_related(api_id, depth=depth)
        related_apis = [r for r in related if self.graph.has_api(r)]

        dependencies = self.graph.find_dependencies(api_id)
        similar = self.graph.find_similar(api_id)[:3]

        return {
            "api": api_info,
            "related_apis": related_apis,
            "dependencies": dependencies,
            "similar_apis": similar,
        }

    def get_stats(self) -> GraphStats:
        """Get graph statistics."""
        return self.graph.get_stats()

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query."""
        # Simple keyword extraction
        words = query.lower().split()
        # Filter common words
        stop_words = {"的", "是", "在", "和", "与", "或", "有", "什么", "怎么", "如何", "请", "帮我"}
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        return keywords

    def _matches_filters(self, api_info: Dict[str, Any], filters: QueryFilters) -> bool:
        """Check if API matches filters."""
        if not api_info:
            return False

        # Check tags
        if filters.tags:
            api_tags = api_info.get("tags", "").split(",")
            if not any(tag in api_tags for tag in filters.tags):
                return False

        # Check deprecated
        if filters.deprecated is not None:
            is_deprecated = api_info.get("deprecated", False)
            if is_deprecated != filters.deprecated:
                return False

        # Check version
        if filters.version:
            if api_info.get("version") != filters.version:
                return False

        # Check path prefix
        if filters.path_prefix:
            path = api_info.get("path", "")
            if not path.startswith(filters.path_prefix):
                return False

        # Check methods
        if filters.methods:
            method = api_info.get("method", "").lower()
            if method not in filters.methods:
                return False

        return True
