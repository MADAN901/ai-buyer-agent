from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_

from app.config import get_settings
from app.core.replenishment import compute_replenishment
from app.db.database import SessionLocal
from app.models.models import Approval, Budget, Forecast, FulfillmentNode, Inventory, Policy, PurchaseOrder, SalesHistory, Supplier, SupplierProduct
from app.policy.engine import PolicyEngine

settings = get_settings()
policy_engine = PolicyEngine()


def _db() -> SessionLocal:
    return SessionLocal()


def get_inventory(sku: str, node_id: str) -> dict[str, Any]:
    db = _db()
    try:
        row = db.query(Inventory).filter_by(sku=sku, node_id=node_id).one_or_none()
        if not row:
            return {"sku": sku, "node_id": node_id, "on_hand": 0, "reserved": 0, "damaged": 0, "available": 0}
        return {
            "sku": sku,
            "node_id": node_id,
            "on_hand": row.on_hand,
            "reserved": row.reserved,
            "damaged": row.damaged,
            "available": max(0, row.on_hand - row.reserved - row.damaged),
        }
    finally:
        db.close()


def get_demand_forecast(sku: str, node_id: str, horizon_days: int = 14) -> dict[str, Any]:
    db = _db()
    try:
        row = db.query(Forecast).filter_by(sku=sku, node_id=node_id).order_by(Forecast.generated_at.desc()).first()
        if not row:
            return {"sku": sku, "node_id": node_id, "expected_daily_demand": 0.0, "model_accuracy": 0.0, "stale": True}
        return {
            "sku": sku,
            "node_id": node_id,
            "expected_daily_demand": row.expected_daily_demand,
            "model_accuracy": 1.0 - row.mape,
            "stale": (datetime.utcnow() - row.generated_at).days > 7,
            "mape": row.mape,
        }
    finally:
        db.close()


def get_sales_history(sku: str, node_id: str, days: int = 30) -> list[dict[str, Any]]:
    db = _db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = db.query(SalesHistory).filter(
            and_(SalesHistory.sku == sku, SalesHistory.node_id == node_id, SalesHistory.date >= cutoff)
        ).order_by(SalesHistory.date.asc()).all()
        return [
            {"date": row.date.isoformat(), "units_sold": row.units_sold, "promo_flag": row.promo_flag, "stockout_flag": row.stockout_flag}
            for row in rows
        ]
    finally:
        db.close()


def get_open_purchase_orders(sku: str | None = None, node_id: str | None = None) -> list[dict[str, Any]]:
    db = _db()
    try:
        query = db.query(PurchaseOrder)
        if sku:
            query = query.filter(PurchaseOrder.sku == sku)
        if node_id:
            query = query.filter(PurchaseOrder.node_id == node_id)
        rows = query.filter(PurchaseOrder.status.notin_(["RECEIVED", "CANCELLED"])).all()
        return [
            {
                "po_id": row.po_id,
                "supplier_id": row.supplier_id,
                "sku": row.sku,
                "node_id": row.node_id,
                "qty": row.qty,
                "status": row.status,
                "expected_arrival": row.expected_arrival.isoformat() if row.expected_arrival else None,
            }
            for row in rows
        ]
    finally:
        db.close()


def get_supplier_terms(supplier_id: str, sku: str) -> dict[str, Any]:
    db = _db()
    try:
        supplier = db.query(Supplier).filter_by(supplier_id=supplier_id).one_or_none()
        if not supplier:
            return {"supplier_id": supplier_id, "status": "unknown"}
        product = db.query(SupplierProduct).filter_by(supplier_id=supplier_id, sku=sku).one_or_none()
        return {
            "supplier_id": supplier_id,
            "status": supplier.status,
            "lead_time_days": supplier.lead_time_days,
            "lead_time_std_days": supplier.lead_time_std_days,
            "moq": product.moq if product else supplier.moq_units,
            "order_multiple": product.order_multiple if product else supplier.order_multiple,
            "price": product.price if product else supplier.price_per_unit,
            "max_qty": product.max_qty if product else 999999,
            "fill_rate": supplier.fill_rate_pct,
            "on_time_pct": supplier.on_time_pct,
            "payment_terms": supplier.payment_terms,
        }
    finally:
        db.close()


def list_alternate_suppliers(sku: str, node_id: str) -> list[dict[str, Any]]:
    db = _db()
    try:
        rows = db.query(SupplierProduct).filter_by(sku=sku).join(Supplier, SupplierProduct.supplier_id == Supplier.supplier_id).all()
        results = []
        for row in rows:
            supplier = db.query(Supplier).filter_by(supplier_id=row.supplier_id).one()
            results.append({
                "supplier_id": row.supplier_id,
                "name": supplier.name,
                "price": row.price,
                "lead_time_days": supplier.lead_time_days,
                "fill_rate": supplier.fill_rate_pct,
                "status": supplier.status,
                "total_cost_score": row.price * (1.2 - supplier.fill_rate_pct),
            })
        return sorted(results, key=lambda item: (item["total_cost_score"], item["lead_time_days"]))
    finally:
        db.close()


def get_budget(category: str | None = None, node_id: str | None = None) -> dict[str, Any]:
    db = _db()
    try:
        query = db.query(Budget)
        if category:
            query = query.filter(Budget.category == category)
        if node_id:
            query = query.filter(Budget.node_id == node_id)
        rows = query.all()
        total = sum(row.total for row in rows)
        committed = sum(row.committed for row in rows)
        return {"category": category, "node_id": node_id, "total": total, "committed": committed, "remaining": max(0.0, total - committed)}
    finally:
        db.close()


def get_storage_capacity(node_id: str) -> dict[str, Any]:
    db = _db()
    try:
        row = db.query(FulfillmentNode).filter_by(node_id=node_id).one_or_none()
        if not row:
            return {"node_id": node_id, "free_m3": 0.0, "capacity_m3": 0.0, "used_m3": 0.0}
        free_m3 = max(0.0, row.storage_capacity_m3 - row.storage_used_m3)
        return {"node_id": node_id, "free_m3": free_m3, "capacity_m3": row.storage_capacity_m3, "used_m3": row.storage_used_m3, "dry_goods_cap": row.dry_goods_capacity_m3, "cold_chain_cap": row.cold_chain_capacity_m3}
    finally:
        db.close()


def get_policies() -> dict[str, Any]:
    db = _db()
    try:
        rows = db.query(Policy).all()
        return {row.name: row.value for row in rows}
    finally:
        db.close()


def compute_replenishment_tool(sku: str, node_id: str, *, recommended_qty: int | None = None, daily_demand: float | None = None, lead_time_days: int = 7, review_days: int = 3, service_level: float = 0.95, supplier_id: str | None = None, budget_limit: float | None = None, storage_limit: float | None = None, max_cover_days: int | None = None) -> dict[str, Any]:
    db = _db()
    try:
        inv = db.query(Inventory).filter_by(sku=sku, node_id=node_id).one_or_none()
        on_hand = inv.on_hand if inv else 0
        reserved = inv.reserved if inv else 0
        damaged = inv.damaged if inv else 0
        inbound = sum(row.qty for row in db.query(PurchaseOrder).filter(PurchaseOrder.sku == sku, PurchaseOrder.node_id == node_id, PurchaseOrder.status.in_(["SENT", "CONFIRMED", "PARTIAL", "PENDING_APPROVAL"])) if row.expected_arrival and row.expected_arrival > datetime.utcnow())
        if recommended_qty is None:
            recommended_qty = 0
        supplier = None if not supplier_id else db.query(Supplier).filter_by(supplier_id=supplier_id).one_or_none()
        supplier_moq = supplier.moq_units if supplier else 1
        order_multiple = supplier.order_multiple if supplier else 1
        max_qty = None if not supplier_id else db.query(SupplierProduct).filter_by(supplier_id=supplier_id, sku=sku).one_or_none().max_qty if db.query(SupplierProduct).filter_by(supplier_id=supplier_id, sku=sku).one_or_none() else None
        if budget_limit is None:
            budget_row = db.query(Budget).filter((Budget.node_id == node_id) | (Budget.category == "fresh")).first()
            budget_limit = budget_row.remaining if budget_row else 5000.0
        if storage_limit is None:
            node = db.query(FulfillmentNode).filter_by(node_id=node_id).one_or_none()
            storage_limit = node.storage_capacity_m3 if node else 1000.0
        if daily_demand is None:
            daily_demand = db.query(Forecast).filter_by(sku=sku, node_id=node_id).order_by(Forecast.generated_at.desc()).first().expected_daily_demand if db.query(Forecast).filter_by(sku=sku, node_id=node_id).order_by(Forecast.generated_at.desc()).first() else 0.0
        unit_cost = db.query(Product).filter_by(sku=sku).one().unit_cost if db.query(Product).filter_by(sku=sku).one_or_none() else 0.0
        volume = db.query(Product).filter_by(sku=sku).one().unit_volume_m3 if db.query(Product).filter_by(sku=sku).one_or_none() else 0.0
        result = compute_replenishment(
            sku=sku,
            node_id=node_id,
            on_hand=on_hand,
            reserved=reserved,
            damaged=damaged,
            inbound_po_qty=inbound,
            daily_demand=daily_demand,
            lead_time_days=lead_time_days,
            review_days=review_days,
            service_level=service_level,
            supplier_moq=supplier_moq,
            order_multiple=order_multiple,
            max_qty=max_qty,
            budget_limit=budget_limit,
            storage_limit=storage_limit,
            max_cover_days=max_cover_days,
            unit_cost=unit_cost,
            unit_volume=volume,
            fill_rate=supplier.fill_rate_pct if supplier else 1.0,
        )
        return result
    finally:
        db.close()


def create_purchase_order(supplier_id: str, sku: str, node_id: str, qty: int, reason: str = "") -> dict[str, Any]:
    db = _db()
    try:
        product = db.query(SupplierProduct).filter_by(supplier_id=supplier_id, sku=sku).one_or_none()
        unit_price = product.price if product else 0.0
        po_id = f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{abs(hash((supplier_id, sku, node_id, qty, reason))) % 10000}"
        po = PurchaseOrder(
            po_id=po_id,
            supplier_id=supplier_id,
            sku=sku,
            node_id=node_id,
            qty=qty,
            unit_price=unit_price,
            status="DRAFT",
            created_by="agent",
            expected_arrival=datetime.utcnow() + timedelta(days=7),
            reason=reason,
            version=1,
        )
        db.add(po)
        db.commit()
        return {"ok": True, "po_id": po_id, "status": po.status, "qty": qty}
    finally:
        db.close()


def modify_purchase_order(po_id: str, new_qty: int | None = None, new_eta: str | None = None, new_supplier: str | None = None, reason: str = "") -> dict[str, Any]:
    db = _db()
    try:
        po = db.query(PurchaseOrder).filter_by(po_id=po_id).one_or_none()
        if not po:
            return {"ok": False, "error": "PO not found"}
        if new_qty is not None:
            po.qty = new_qty
        if new_eta:
            po.expected_arrival = datetime.fromisoformat(new_eta)
        if new_supplier:
            po.supplier_id = new_supplier
        po.reason = reason or po.reason
        po.version += 1
        db.commit()
        return {"ok": True, "po_id": po_id, "status": po.status, "updated": {"qty": po.qty, "supplier_id": po.supplier_id, "eta": po.expected_arrival.isoformat()}}
    finally:
        db.close()


def cancel_purchase_order(po_id: str, reason: str = "") -> dict[str, Any]:
    db = _db()
    try:
        po = db.query(PurchaseOrder).filter_by(po_id=po_id).one_or_none()
        if not po:
            return {"ok": False, "error": "PO not found"}
        po.status = "CANCELLED"
        po.reason = reason or po.reason
        db.commit()
        return {"ok": True, "po_id": po_id, "status": "CANCELLED"}
    finally:
        db.close()


def expedite_purchase_order(po_id: str, reason: str = "") -> dict[str, Any]:
    db = _db()
    try:
        po = db.query(PurchaseOrder).filter_by(po_id=po_id).one_or_none()
        if not po:
            return {"ok": False, "error": "PO not found"}
        po.status = "PENDING_APPROVAL"
        po.reason = reason or po.reason
        db.commit()
        return {"ok": True, "po_id": po_id, "status": po.status}
    finally:
        db.close()


def request_human_approval(po_draft: dict[str, Any], reason: str, risk_level: str, alternatives_considered: list[str]) -> dict[str, Any]:
    db = _db()
    try:
        approval_id = f"APP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{abs(hash(json.dumps(po_draft, sort_keys=True))) % 10000}"
        approval = Approval(approval_id=approval_id, po_id=str(po_draft.get("po_id", "")), reason=reason, risk_level=risk_level, payload=json.dumps({"alternatives_considered": alternatives_considered, "draft": po_draft}), status="PENDING")
        db.add(approval)
        db.commit()
        return {"ok": True, "approval_id": approval_id, "status": "PENDING"}
    finally:
        db.close()


def escalate_to_buyer(summary: str, options: list[str], recommended_option: str, evidence: list[str]) -> dict[str, Any]:
    return {"ok": True, "escalated": True, "summary": summary, "options": options, "recommended_option": recommended_option, "evidence": evidence}


def send_po_to_supplier(po_id: str) -> dict[str, Any]:
    db = _db()
    try:
        po = db.query(PurchaseOrder).filter_by(po_id=po_id).one_or_none()
        if not po:
            return {"ok": False, "error": "PO not found"}
        from app.mock_supplier.api import mock_supplier_response
        response = mock_supplier_response(po.supplier_id, po.qty, po.sku, po.node_id)
        po.status = "SENT"
        po.supplier_response = response["status"]
        db.commit()
        return {"ok": True, **response}
    finally:
        db.close()
