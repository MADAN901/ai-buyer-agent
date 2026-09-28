from __future__ import annotations

import math
from typing import Any


def _round_to_multiple(value: float, multiple: int) -> int:
    if multiple <= 1:
        return max(0, int(round(value)))
    return max(0, int(math.ceil(value / multiple) * multiple))


def compute_replenishment(
    *,
    sku: str,
    node_id: str,
    on_hand: int,
    reserved: int = 0,
    damaged: int = 0,
    inbound_po_qty: int = 0,
    daily_demand: float = 0.0,
    lead_time_days: int = 7,
    review_days: int = 3,
    service_level: float = 0.95,
    supplier_moq: int = 1,
    order_multiple: int = 1,
    max_qty: int | None = None,
    budget_limit: float | None = None,
    storage_limit: float | None = None,
    max_cover_days: int | None = None,
    unit_cost: float = 0.0,
    unit_volume: float = 0.0,
    safety_stock_days: float | None = None,
    fill_rate: float = 1.0,
) -> dict[str, Any]:
    effective_available = max(0, on_hand - reserved - damaged)
    reliable_inbound = max(0, int(round(inbound_po_qty * fill_rate)))
    review_period = max(1, review_days)
    total_horizon = max(1, lead_time_days + review_period)
    expected_use = max(0.0, daily_demand * total_horizon)
    z_value = 1.65 if service_level >= 0.95 else 1.28
    demand_sd = max(0.0, daily_demand * 0.25)
    safety_stock = max(0.0, z_value * demand_sd * math.sqrt(max(1, lead_time_days)))
    if safety_stock_days is not None:
        safety_stock = max(safety_stock, safety_stock_days * daily_demand)
    target_stock = max(0.0, expected_use + safety_stock)
    unconstrained_qty = max(0, int(math.ceil(max(0.0, target_stock - (effective_available + reliable_inbound)))))

    feasible_qty = unconstrained_qty
    binding_constraints: list[str] = []

    if max_qty is not None and feasible_qty > max_qty:
        feasible_qty = max_qty
        binding_constraints.append("max_qty")

    if supplier_moq and feasible_qty > 0 and feasible_qty < supplier_moq:
        feasible_qty = supplier_moq
        binding_constraints.append("moq")

    if order_multiple > 1:
        rounded = _round_to_multiple(feasible_qty, order_multiple)
        if rounded != feasible_qty:
            feasible_qty = rounded
            binding_constraints.append("order_multiple")

    if budget_limit is not None and unit_cost > 0:
        max_budget_qty = int(math.floor(budget_limit / unit_cost)) if unit_cost > 0 else 0
        if feasible_qty > max_budget_qty:
            feasible_qty = max_budget_qty
            binding_constraints.append("budget")

    if storage_limit is not None and unit_volume > 0:
        max_storage_qty = int(math.floor(storage_limit / unit_volume)) if unit_volume > 0 else 0
        if feasible_qty > max_storage_qty:
            feasible_qty = max_storage_qty
            binding_constraints.append("storage")

    if max_cover_days is not None and daily_demand > 0:
        max_cover_qty = max(0, int(math.floor(max_cover_days * daily_demand)))
        if feasible_qty > max_cover_qty:
            feasible_qty = max_cover_qty
            binding_constraints.append("max_cover_days")

    if supplier_moq and feasible_qty > 0 and feasible_qty < supplier_moq:
        feasible_qty = supplier_moq
        binding_constraints.append("moq")

    if order_multiple > 1:
        feasible_qty = _round_to_multiple(feasible_qty, order_multiple)
        if feasible_qty != unconstrained_qty and "order_multiple" not in binding_constraints:
            binding_constraints.append("order_multiple")

    if max_qty is not None and feasible_qty > max_qty:
        feasible_qty = max_qty
        binding_constraints.append("max_qty")

    days_of_cover_after = 0.0
    if daily_demand > 0:
        future_stock = effective_available + reliable_inbound + feasible_qty
        if future_stock > 0:
            days_of_cover_after = future_stock / daily_demand
        else:
            days_of_cover_after = 0.0
    stockout_risk = min(1.0, max(0.0, 1.0 - (effective_available + reliable_inbound) / max(1.0, target_stock)))
    cost = feasible_qty * unit_cost
    volume_m3 = feasible_qty * unit_volume

    return {
        "sku": sku,
        "node_id": node_id,
        "effective_available": effective_available,
        "inbound_within_horizon": reliable_inbound,
        "unconstrained_qty": unconstrained_qty,
        "feasible_qty": feasible_qty,
        "binding_constraints": list(dict.fromkeys(binding_constraints)),
        "days_of_cover_after": round(days_of_cover_after, 2),
        "stockout_risk": round(stockout_risk, 4),
        "cost": round(cost, 2),
        "volume_m3": round(volume_m3, 4),
    }
