"""Vector store using Chroma."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from src.rag.embedder import Embedder


class VectorStore:
    """Vector store using Chroma."""

    def __init__(
        self,
        persist_directory: str = "./data/vectorstore",
        collection_name: str = "api_docs",
        embedder: Optional[Embedder] = None,
    ):
        """Initialize vector store."""
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedder = embedder

        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "API documentation vectors"},
        )

        # LangChain vectorstore wrapper
        self._langchain_store: Optional[Chroma] = None

    def _get_langchain_store(self) -> Chroma:
        """Get LangChain Chroma wrapper."""
        if self._langchain_store is None:
            self._langchain_store = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embedder.embeddings if self.embedder else None,
            )
        return self._langchain_store

    def add_documents(self, documents: List[Document], ids: Optional[List[str]] = None) -> None:
        """Add documents to the store."""
        if not self.embedder:
            raise ValueError("Embedder required for adding documents")

        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        if ids is None:
            ids = [f"doc_{i}" for i in range(len(texts))]

        # Add to Chroma
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

    def add_api_documents(self, apis: List[Any]) -> None:
        """Add API entities as documents."""
        if not self.embedder:
            raise ValueError("Embedder required for adding documents")

        documents = []
        ids = []

        for api in apis:
            doc = Document(
                page_content=api.to_document(),
                metadata={
                    "api_id": api.id,
                    "path": api.path,
                    "method": api.method.value,
                    "tags": ",".join(api.tags),
                },
            )
            documents.append(doc)
            ids.append(api.id)

        self.add_documents(documents, ids)

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Search for similar documents."""
        if not self.embedder:
            raise ValueError("Embedder required for similarity search")

        store = self._get_langchain_store()
        return store.similarity_search(
            query=query,
            k=k,
            filter=filter,
        )

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[tuple[Document, float]]:
        """Search for similar documents with scores."""
        if not self.embedder:
            raise ValueError("Embedder required for similarity search")

        store = self._get_langchain_store()
        return store.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter,
        )

    def get_by_id(self, id: str) -> Optional[Document]:
        """Get document by ID."""
        result = self.collection.get(ids=[id])
        if not result["documents"]:
            return None

        return Document(
            page_content=result["documents"][0],
            metadata=result["metadatas"][0],
        )

    def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs."""
        self.collection.delete(ids=ids)

    def reset(self) -> None:
        """Reset the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "API documentation vectors"},
        )
        self._langchain_store = None

    def count(self) -> int:
        """Get document count."""
        return self.collection.count()
