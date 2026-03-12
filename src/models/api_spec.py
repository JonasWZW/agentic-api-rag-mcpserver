"""API specification models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class HTTPMethod(str, Enum):
    """HTTP methods."""

    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"
    OPTIONS = "options"
    HEAD = "head"


class EdgeType(str, Enum):
    """Knowledge graph edge types."""

    DEPENDS_ON = "depends_on"
    SIMILAR_TO = "similar_to"
    PART_OF = "part_of"
    CALLS = "calls"
    HAS_PARAM = "has_param"
    USES_SCHEMA = "uses_schema"
    HAS_TAG = "has_tag"
    SAME_OP = "same_op"


class NodeType(str, Enum):
    """Knowledge graph node types."""

    API = "API"
    SCHEMA = "Schema"
    TAG = "Tag"
    PARAMETER = "Parameter"
    OPERATION = "Operation"


@dataclass
class Parameter:
    """API parameter."""

    name: str
    location: str  # query, path, header, cookie
    type: str
    required: bool = False
    description: Optional[str] = None
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


@dataclass
class Schema:
    """API schema."""

    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    description: Optional[str] = None
    example: Optional[Dict[str, Any]] = None


@dataclass
class APIEntity:
    """API entity."""

    id: str
    path: str
    method: HTTPMethod
    summary: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    request_schema: Optional[Schema] = None
    response_schema: Optional[Schema] = None
    security: List[str] = field(default_factory=list)
    deprecated: bool = False
    version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "method": self.method.value,
            "summary": self.summary,
            "description": self.description,
            "tags": self.tags,
            "parameters": [
                {
                    "name": p.name,
                    "location": p.location,
                    "type": p.type,
                    "required": p.required,
                    "description": p.description,
                }
                for p in self.parameters
            ],
            "request_schema": self.request_schema.properties if self.request_schema else None,
            "response_schema": self.response_schema.properties if self.response_schema else None,
            "security": self.security,
            "deprecated": self.deprecated,
            "version": self.version,
        }

    def to_document(self) -> str:
        """Convert to document for RAG."""
        doc = f"""
[API: {self.method.value.upper()} {self.path}]
[Summary: {self.summary}]
[Tags: {", ".join(self.tags)}]

[Description]
{self.description or "无"}

[Request Parameters]
"""
        if self.parameters:
            for p in self.parameters:
                req = "required" if p.required else "optional"
                doc += f"- {p.name}: {p.type} ({req})"
                if p.description:
                    doc += f" - {p.description}"
                doc += "\n"
        else:
            doc += "无\n"

        doc += "\n[Response]\n"
        if self.response_schema:
            doc += str(self.response_schema.properties)
        else:
            doc += "无\n"

        if self.security:
            doc += f"\n[Security]\n{', '.join(self.security)}\n"

        return doc


@dataclass
class GraphNode:
    """Knowledge graph node."""

    id: str
    type: NodeType
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Knowledge graph edge."""

    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    reason: Optional[str] = None
