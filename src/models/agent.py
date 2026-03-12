"""Agent models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Intent(str, Enum):
    """Intent types."""

    QUERY = "query"
    CALL = "call"
    UNDERSTAND = "understand"
    COMPARE = "compare"
    RECOMMEND = "recommend"
    DEBUG = "debug"


@dataclass
class Entity:
    """Extracted entity from query."""

    type: str  # domain, tag, api_name, operation
    value: str
    confidence: float = 1.0


@dataclass
class IntentResult:
    """Intent classification result."""

    intent: Intent
    confidence: float
    reasoning: str
    entities: List[Entity] = field(default_factory=list)


@dataclass
class QueryFilters:
    """Query filters."""

    tags: List[str] = field(default_factory=list)
    version: Optional[str] = None
    deprecated: Optional[bool] = None
    path_prefix: Optional[str] = None
    methods: List[str] = field(default_factory=list)


@dataclass
class QueryOptions:
    """Query options."""

    include_examples: bool = True
    top_k: int = 5


@dataclass
class RetrievalResult:
    """Retrieval result."""

    api_id: str
    score: float
    source: str  # "graph", "rag", "direct"


@dataclass
class SubAgentResult:
    """SubAgent execution result."""

    answer: str
    apis: List[Dict[str, Any]] = field(default_factory=list)
    code_examples: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    subagent_name: str = ""
    intent: Optional[Intent] = None


@dataclass
class AgentResponse:
    """Agent response."""

    success: bool
    intent: Optional[Intent] = None
    answer: str = ""
    apis: List[Dict[str, Any]] = field(default_factory=list)
    subagent_used: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class RouteDecision:
    """Route decision."""

    target_subagents: List[str]
    strategy: str  # "single", "parallel", "chain"
    execution_order: List[str] = field(default_factory=list)
