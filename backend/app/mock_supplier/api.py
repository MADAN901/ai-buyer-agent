from __future__ import annotations

import os
from typing import Any


def mock_supplier_response(supplier_id: str, qty: int, sku: str, node_id: str) -> dict[str, Any]:
    chaos = os.getenv("MOCK_SUPPLIER_CHAOS", "false").lower() == "true"
    if not chaos:
        return {"status": "confirmed", "qty_confirmed": qty, "eta_days": 5, "price": 0.0, "message": "Confirmed."}

    if supplier_id == "SUP-2":
        return {"status": "partial", "qty_confirmed": max(1, qty // 2), "eta_days": 8, "price": 0.0, "message": "Partial fill available."}
    if supplier_id == "SUP-3":
        return {"status": "rejected", "qty_confirmed": 0, "eta_days": 0, "price": 0.0, "message": "Rejected due to stock limit."}
    return {"status": "timeout", "qty_confirmed": 0, "eta_days": 0, "price": 0.0, "message": "Supplier timed out."}
