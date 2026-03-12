"""Configuration management for Agentic API RAG MCP Server."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """LLM configuration."""

    provider: str = Field(default="openai", description="LLM provider: openai, chatglm")
    model: str = Field(default="gpt-4", description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="Custom API base URL")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=2000, description="Max tokens for generation")

    class Config:
        env_prefix = "LLM_"


class MCPConfig(BaseSettings):
    """MCP Server configuration."""

    server_name: str = Field(default="agentic-api-rag", description="MCP server name")
    version: str = Field(default="1.0.0", description="Server version")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    class Config:
        env_prefix = "MCP_"


class RAGConfig(BaseSettings):
    """RAG configuration."""

    vector_store: str = Field(default="chroma", description="Vector store type")
    embedding_model: str = Field(default="text-embedding-ada-002", description="Embedding model")
    chunk_size: int = Field(default=1000, description="Chunk size for text splitting")
    chunk_overlap: int = Field(default=200, description="Chunk overlap")
    top_k: int = Field(default=5, description="Default top k for retrieval")

    class Config:
        env_prefix = "RAG_"


class KnowledgeGraphConfig(BaseSettings):
    """Knowledge Graph configuration."""

    graph_type: str = Field(default="networkx", description="Graph type")
    default_depth: int = Field(default=2, description="Default search depth")

    class Config:
        env_prefix = "KG_"


class Settings(BaseSettings):
    """Main settings."""

    # Application settings
    app_name: str = Field(default="Agentic API RAG MCP Server")
    debug: bool = Field(default=False, description="Debug mode")
    base_dir: Path = Field(default=Path(__file__).parent.parent.parent)

    # Configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    kg: KnowledgeGraphConfig = Field(default_factory=KnowledgeGraphConfig)

    # Paths
    apis_dir: Path = Field(default=Path("apis"), description="Directory containing OpenAPI specs")
    config_dir: Path = Field(default=Path("config"), description="Configuration directory")

    class Config:
        env_prefix = "APP_"

    @classmethod
    def from_yaml(cls, config_path: str) -> "Settings":
        """Load settings from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            return cls()

        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        return cls(
            llm=LLMConfig(**config_data.get("llm", {})),
            mcp=MCPConfig(**config_data.get("mcp", {})),
            rag=RAGConfig(**config_data.get("rag", {})),
            kg=KnowledgeGraphConfig(**config_data.get("kg", {})),
        )


# Global settings instance
settings = Settings()
