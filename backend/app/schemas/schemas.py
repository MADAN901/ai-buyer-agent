from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DecisionEnum = Literal["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE_FURTHER", "ESCALATE"]


class ScenarioFixture(BaseModel):
    id: str
    title: str
    description: str
    expected_outcome: str


class ReplenishmentResult(BaseModel):
    sku: str
    node_id: str
    unconstrained_qty: int
    feasible_qty: int
    binding_constraints: list[str] = Field(default_factory=list)
    days_of_cover_after: float
    stockout_risk: float
    cost: float
    volume_m3: float
    effective_available: int
    inbound_within_horizon: int


class PolicyViolation(BaseModel):
    rule: str
    expected: Any
    actual: Any
    severity: str = "error"


class PolicyCheckResult(BaseModel):
    passed: bool
    violations: list[PolicyViolation] = Field(default_factory=list)
    suggested_fix: str = ""


class ToolCallResult(BaseModel):
    ok: bool
    result: Any = None
    error: str | None = None


class AgentDecision(BaseModel):
    decision: DecisionEnum
    quantity: int | None = None
    supplier_id: str | None = None
    node_id: str | None = None
    confidence: float = 0.0
    reasoning: str = ""
    factors: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    action_taken: str | None = None


class AgentRunResponse(BaseModel):
    run_id: str
    status: str
    final_decision: str
    steps: list[dict[str, Any]] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    approve: bool
    comment: str = ""
