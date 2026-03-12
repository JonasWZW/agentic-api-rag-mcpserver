"""RAG retriever."""

from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from src.models import APIEntity, QueryFilters, RetrievalResult
from src.rag.store import VectorStore


class Retriever:
    """RAG retriever for API search."""

    def __init__(self, vector_store: VectorStore):
        """Initialize retriever."""
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        filters: Optional[QueryFilters] = None,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """Search for relevant APIs."""
        # Build filter dict for Chroma
        filter_dict = None
        if filters:
            filter_dict = self._build_filter(filters)

        # Search
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=top_k * 2,  # Get more for filtering
            filter=filter_dict,
        )

        # Process results
        retrieval_results = []
        seen_ids = set()

        for doc, score in results:
            api_id = doc.metadata.get("api_id")
            if api_id in seen_ids:
                continue
            seen_ids.add(api_id)

            # Determine source
            source = "rag"

            retrieval_results.append(
                RetrievalResult(
                    api_id=api_id,
                    score=float(score),
                    source=source,
                )
            )

            if len(retrieval_results) >= top_k:
                break

        return retrieval_results

    def get_api_by_id(self, api_id: str) -> Optional[Document]:
        """Get API document by ID."""
        return self.vector_store.get_by_id(api_id)

    def batch_get(self, api_ids: List[str]) -> List[Optional[Document]]:
        """Get multiple APIs by IDs."""
        results = []
        for api_id in api_ids:
            doc = self.vector_store.get_by_id(api_id)
            results.append(doc)
        return results

    def _build_filter(self, filters: QueryFilters) -> Dict[str, Any]:
        """Build Chroma filter from QueryFilters."""
        filter_dict = {}

        if filters.tags:
            # Chroma doesn't support $in for metadata, use $contains
            # We'll handle tag filtering after retrieval
            pass

        if filters.deprecated is not None:
            filter_dict["deprecated"] = filters.deprecated

        if filters.version:
            filter_dict["version"] = filters.version

        if filters.path_prefix:
            filter_dict["path"] = {"$contains": filters.path_prefix}

        return filter_dict if filter_dict else None

    def filter_by_tags(self, results: List[RetrievalResult], tags: List[str]) -> List[RetrievalResult]:
        """Filter results by tags."""
        if not tags:
            return results

        filtered = []
        for result in results:
            doc = self.vector_store.get_by_id(result.api_id)
            if doc:
                api_tags = doc.metadata.get("tags", "").split(",")
                if any(tag in api_tags for tag in tags):
                    filtered.append(result)

        return filtered
