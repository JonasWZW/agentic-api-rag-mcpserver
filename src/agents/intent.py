"""Intent classifier for analyzing user query intent."""

import re
from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from src.models import Entity, Intent, IntentResult, QueryFilters


# Keyword patterns for quick fallback
KEYWORD_PATTERNS = {
    Intent.QUERY: ["哪里", "怎么", "哪些", "什么接口", "找", "查询", "哪个", "请告诉我", "我要找"],
    Intent.CALL: ["调用", "执行", "请求", "使用", "调用一下", "帮我调用"],
    Intent.UNDERSTAND: ["是什么", "怎么工作", "原理", "流程", "是什么意思", "解释"],
    Intent.COMPARE: ["区别", "差异", "哪个好", "对比", "比较", "不同", "对比一下"],
    Intent.RECOMMEND: ["推荐", "类似", "其他", "代替", "还有什么", "有没有其他"],
    Intent.DEBUG: ["错误", "失败", "报错", "问题", "解决", "为什么", "调试", "修复"],
}


class IntentClassifier:
    """Classify user query intent using LLM or keyword matching."""

    def __init__(self, llm: Optional[BaseChatModel] = None):
        """Initialize intent classifier."""
        self.llm = llm

    async def classify(self, query: str, history: str = "") -> IntentResult:
        """Classify the query intent."""
        # Try LLM classification first if available
        if self.llm:
            try:
                return await self._llm_classify(query, history)
            except Exception as e:
                print(f"LLM classification failed: {e}, falling back to keyword matching")

        # Fallback to keyword matching
        return self._keyword_classify(query)

    async def _llm_classify(self, query: str, history: str) -> IntentResult:
        """Use LLM for intent classification."""
        from langchain_core.prompts import PromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = PromptTemplate.from_template(
            """分析用户查询的意图。

可选意图类型:
- QUERY: 查询 API 信息（位置、参数、用法）
- CALL: 调用/执行 API
- UNDERSTAND: 理解 API 原理和工作流程
- COMPARE: 比较 API 差异
- RECOMMEND: 推荐相关 API
- DEBUG: 调试问题

用户查询: {query}
历史对话: {history}

请以 JSON 格式输出:
{{
    "intent": "QUERY",
    "confidence": 0.95,
    "reasoning": "分类理由",
    "entities": [
        {{"type": "domain", "value": "user"}},
        {{"type": "operation", "value": "login"}}
    ]
}}
"""
        )

        # Use structured output if possible
        try:
            from langchain_core.output_parsers import JsonOutputParser

            chain = prompt | self.llm | JsonOutputParser()
            result = await chain.ainvoke({"query": query, "history": history})

            return IntentResult(
                intent=Intent(result.get("intent", "query").lower()),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", ""),
                entities=[
                    Entity(type=e.get("type", ""), value=e.get("value", ""), confidence=e.get("confidence", 1.0))
                    for e in result.get("entities", [])
                ],
            )
        except Exception as e:
            # Fallback: parse from text
            response = await self.llm.ainvoke(prompt.format(query=query, history=history))
            return self._parse_llm_response(response.content)

    def _parse_llm_response(self, response: str) -> IntentResult:
        """Parse LLM response to IntentResult."""
        # Extract intent
        for intent in Intent:
            if intent.value in response.lower():
                confidence = 0.8
                break
        else:
            intent = Intent.QUERY
            confidence = 0.5

        # Extract entities
        entities = self._extract_entities(response)

        return IntentResult(
            intent=intent,
            confidence=confidence,
            reasoning="LLM classification",
            entities=entities,
        )

    def _extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text."""
        entities = []

        # Extract domains/tags
        domains = ["user", "order", "payment", "product", "auth", "admin"]
        for domain in domains:
            if domain in text.lower():
                entities.append(Entity(type="domain", value=domain, confidence=0.8))

        # Extract operations
        operations = ["login", "create", "delete", "update", "get", "list"]
        for op in operations:
            if op in text.lower():
                entities.append(Entity(type="operation", value=op, confidence=0.8))

        return entities

    def _keyword_classify(self, query: str) -> IntentResult:
        """Keyword-based intent classification."""
        query_lower = query.lower()

        # Score each intent
        scores = {}
        for intent, keywords in KEYWORD_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            # Default to QUERY
            return IntentResult(
                intent=Intent.QUERY,
                confidence=0.5,
                reasoning="Default to QUERY intent",
                entities=self._extract_entities(query),
            )

        # Get highest scoring intent
        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] * 0.3, 0.9)

        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            reasoning=f"Matched keywords: {[kw for kw in KEYWORD_PATTERNS[best_intent] if kw in query_lower]}",
            entities=self._extract_entities(query),
        )


def extract_filters_from_query(query: str) -> QueryFilters:
    """Extract filters from query text."""
    filters = QueryFilters()

    # Extract tags from query
    known_tags = ["user", "order", "payment", "product", "auth", "admin", "customer"]
    found_tags = []
    for tag in known_tags:
        if tag in query.lower():
            found_tags.append(tag)

    if found_tags:
        filters.tags = found_tags

    # Check for deprecated
    if "废弃" in query or "deprecated" in query.lower():
        filters.deprecated = True
    elif "最新" in query or "current" in query.lower():
        filters.deprecated = False

    # Extract version
    version_match = re.search(r"v(\d+)", query.lower())
    if version_match:
        filters.version = f"v{version_match.group(1)}"

    # Extract methods
    methods = ["get", "post", "put", "patch", "delete"]
    found_methods = [m for m in methods if m in query.lower()]
    if found_methods:
        filters.methods = found_methods

    return filters
