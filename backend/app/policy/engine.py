from __future__ import annotations

from typing import Any

from app.schemas.schemas import PolicyCheckResult, PolicyViolation


class PolicyEngine:
    def __init__(self, rules: dict[str, Any] | None = None):
        self.rules = rules or {}

    def validate(self, *, qty: int, supplier_id: str | None, node_id: str | None, unit_price: float, budget_remaining: float, storage_free_m3: float, volume_m3: float, max_cover_days: float | None = None, min_safety_days: float | None = None, supplier_status: str | None = None, supplier_moq: int = 1, order_multiple: int = 1, supplier_max_qty: int | None = None, auto_approve_limit: float = 5000.0) -> PolicyCheckResult:
        violations: list[PolicyViolation] = []
        if supplier_status and supplier_status.lower() == "blocked":
            violations.append(PolicyViolation(rule="supplier_status", expected="active", actual=supplier_status, severity="error"))
        if supplier_moq and qty > 0 and qty < supplier_moq:
            violations.append(PolicyViolation(rule="supplier_moq", expected=f">= {supplier_moq}", actual=qty, severity="error"))
        if order_multiple > 1 and qty % order_multiple != 0:
            violations.append(PolicyViolation(rule="order_multiple", expected=f"multiple of {order_multiple}", actual=qty, severity="error"))
        if supplier_max_qty is not None and qty > supplier_max_qty:
            violations.append(PolicyViolation(rule="supplier_max_qty", expected=f"<= {supplier_max_qty}", actual=qty, severity="error"))
        if budget_remaining < 0: 
            violations.append(PolicyViolation(rule="budget", expected="non-negative", actual=budget_remaining, severity="error"))
        if unit_price * qty > auto_approve_limit:
            violations.append(PolicyViolation(rule="approval_threshold", expected=f"<= {auto_approve_limit}", actual=unit_price * qty, severity="warning"))
        if volume_m3 > storage_free_m3:
            violations.append(PolicyViolation(rule="storage", expected=f"<= {storage_free_m3}m3", actual=volume_m3, severity="error"))
        if max_cover_days is not None and max_cover_days < 0:
            violations.append(PolicyViolation(rule="max_cover_days", expected="positive", actual=max_cover_days, severity="error"))
        if min_safety_days is not None and min_safety_days < 0:
            violations.append(PolicyViolation(rule="min_safety_days", expected="positive", actual=min_safety_days, severity="error"))

        suggested_fix = "Reduce quantity to respect supplier and storage constraints." if violations else "No policy violations detected."
        return PolicyCheckResult(passed=not violations, violations=violations, suggested_fix=suggested_fix)
