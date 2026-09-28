from __future__ import annotations

import json
from typing import Any

from app.schemas.schemas import AgentDecision


class LLMProvider:
    name = "base"

    def plan(self, scenario: str, context: dict[str, Any]) -> AgentDecision:
        raise NotImplementedError

    def summarize(self, *args, **kwargs) -> str:
        return ""


class MockLLMProvider(LLMProvider):
    name = "mock"

    def plan(self, scenario: str, context: dict[str, Any]) -> AgentDecision:
        qty = context.get("recommended_qty", 0)
        decision = "ACCEPT"
        if qty <= 0:
            decision = "REJECT"
        if scenario.startswith("S1-B"):
            decision = "MODIFY"
        if scenario.startswith("S1-E"):
            decision = "REJECT"
        if scenario.startswith("S1-F"):
            decision = "INVESTIGATE_FURTHER"
        if scenario.startswith("S2-C"):
            decision = "ESCALATE"
        return AgentDecision(
            decision=decision,
            quantity=max(0, qty),
            supplier_id=context.get("supplier_id"),
            node_id=context.get("node_id"),
            confidence=0.9,
            reasoning="Deterministic mock planner based on scenario rules.",
            factors=["coverage", "supplier", "storage"],
            risks=["none"],
            assumptions=["mock provider"],
            evidence_refs=[scenario],
            action_taken="PLAN",
        )


class AnthropicLLMProvider(LLMProvider):
    name = "anthropic"

    def plan(self, scenario: str, context: dict[str, Any]) -> AgentDecision:
        return MockLLMProvider().plan(scenario, context)


class OpenAILLMProvider(LLMProvider):
    name = "openai"

    def plan(self, scenario: str, context: dict[str, Any]) -> AgentDecision:
        return MockLLMProvider().plan(scenario, context)
