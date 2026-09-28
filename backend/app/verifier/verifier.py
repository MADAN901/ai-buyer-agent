from __future__ import annotations

from typing import Any


def verify_po_outcome(po: dict[str, Any], expected_qty: int, expected_eta_days: int | None = None, expected_status: str | None = None) -> dict[str, Any]:
    mismatches = []
    if po.get("qty") != expected_qty:
        mismatches.append({"field": "qty", "expected": expected_qty, "actual": po.get("qty")})
    if expected_eta_days is not None and po.get("expected_arrival_days") is not None:
        if po.get("expected_arrival_days") != expected_eta_days:
            mismatches.append({"field": "expected_arrival_days", "expected": expected_eta_days, "actual": po.get("expected_arrival_days")})
    if expected_status is not None and po.get("status") != expected_status:
        mismatches.append({"field": "status", "expected": expected_status, "actual": po.get("status")})
    return {"passed": not mismatches, "mismatches": mismatches}
