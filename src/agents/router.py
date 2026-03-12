"""Router for routing queries to appropriate SubAgents."""

from typing import List, Optional

from src.models import Intent, IntentResult, QueryFilters, RouteDecision


class Router:
    """Route queries to appropriate SubAgents."""

    def __init__(self, sub_agents: dict[str, dict]):
        """Initialize router."""
        self.sub_agents = sub_agents  # {name: {domain, tags}}

    def route(
        self,
        intent: IntentResult,
        filters: Optional[QueryFilters] = None,
    ) -> RouteDecision:
        """Route query to SubAgents."""
        # Strategy 1: Direct API ID specified
        # (would be handled separately)

        # Strategy 2: Based on intent type
        if intent.intent == Intent.COMPARE:
            return self._route_compare(intent, filters)
        elif intent.intent == Intent.RECOMMEND:
            return self._route_recommend(intent, filters)

        # Strategy 3: Based on entities and tags
        target_agents = self._find_target_agents(intent, filters)

        if len(target_agents) == 0:
            # Fallback: use all agents
            target_agents = list(self.sub_agents.keys())
            return RouteDecision(
                target_subagents=target_agents,
                strategy="single",
                execution_order=target_agents[:1],
            )
        elif len(target_agents) == 1:
            return RouteDecision(
                target_subagents=target_agents,
                strategy="single",
                execution_order=target_agents,
            )
        else:
            return RouteDecision(
                target_subagents=target_agents,
                strategy="parallel",
                execution_order=target_agents,
            )

    def _route_compare(self, intent: IntentResult, filters: Optional[QueryFilters]) -> RouteDecision:
        """Route for compare intent - multiple agents."""
        target_agents = self._find_target_agents(intent, filters)

        if len(target_agents) < 2:
            # Need at least 2 for comparison
            all_agents = list(self.sub_agents.keys())
            return RouteDecision(
                target_subagents=all_agents[:2],
                strategy="parallel",
                execution_order=all_agents[:2],
            )

        return RouteDecision(
            target_subagents=target_agents,
            strategy="parallel",
            execution_order=target_agents,
        )

    def _route_recommend(self, intent: IntentResult, filters: Optional[QueryFilters]) -> RouteDecision:
        """Route for recommend intent - cross agents."""
        target_agents = self._find_target_agents(intent, filters)

        return RouteDecision(
            target_subagents=target_agents if target_agents else list(self.sub_agents.keys()),
            strategy="parallel",
            execution_order=target_agents if target_agents else list(self.sub_agents.keys()),
        )

    def _find_target_agents(self, intent: IntentResult, filters: Optional[QueryFilters]) -> List[str]:
        """Find target agents based on entities and filters."""
        target_agents = []

        # Priority 1: Match from entities
        for entity in intent.entities:
            if entity.type == "domain" or entity.type == "tag":
                matched = self._match_agents_by_tag(entity.value)
                target_agents.extend(matched)

        # Priority 2: Match from filters
        if filters and filters.tags:
            for tag in filters.tags:
                matched = self._match_agents_by_tag(tag)
                target_agents.extend(matched)

        # Deduplicate
        return list(set(target_agents))

    def _match_agents_by_tag(self, tag: str) -> List[str]:
        """Match agents that handle this tag."""
        matched = []
        tag_lower = tag.lower()

        for name, config in self.sub_agents.items():
            agent_tags = config.get("tags", [])
            if any(tag_lower in t.lower() for t in agent_tags):
                matched.append(name)

        return matched
