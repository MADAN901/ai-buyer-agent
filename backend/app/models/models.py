from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Product(Base):
    __tablename__ = "products"
    sku = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    unit_cost = Column(Float, default=0.0)
    unit_volume_m3 = Column(Float, default=0.0)
    shelf_life_days = Column(Integer, default=0)
    is_perishable = Column(Boolean, default=False)


class FulfillmentNode(Base):
    __tablename__ = "fulfillment_nodes"
    node_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    storage_capacity_m3 = Column(Float, default=0.0)
    storage_used_m3 = Column(Float, default=0.0)
    cold_chain_capacity_m3 = Column(Float, default=0.0)
    dry_goods_capacity_m3 = Column(Float, default=0.0)


class Inventory(Base):
    __tablename__ = "inventory"
    sku = Column(String, primary_key=True)
    node_id = Column(String, ForeignKey("fulfillment_nodes.node_id"), primary_key=True)
    on_hand = Column(Integer, default=0)
    reserved = Column(Integer, default=0)
    damaged = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SalesHistory(Base):
    __tablename__ = "sales_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, nullable=False)
    node_id = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    units_sold = Column(Integer, default=0)
    promo_flag = Column(Boolean, default=False)
    stockout_flag = Column(Boolean, default=False)


class Forecast(Base):
    __tablename__ = "forecasts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, nullable=False)
    node_id = Column(String, nullable=False)
    horizon_days = Column(Integer, default=7)
    expected_daily_demand = Column(Float, default=0.0)
    model_version = Column(String, default="v1")
    generated_at = Column(DateTime, default=datetime.utcnow)
    mape = Column(Float, default=0.1)


class Supplier(Base):
    __tablename__ = "suppliers"
    supplier_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    lead_time_days = Column(Integer, default=5)
    lead_time_std_days = Column(Integer, default=2)
    moq_units = Column(Integer, default=1)
    order_multiple = Column(Integer, default=1)
    price_per_unit = Column(Float, default=0.0)
    fill_rate_pct = Column(Float, default=1.0)
    on_time_pct = Column(Float, default=1.0)
    payment_terms = Column(String, default="NET14")
    status = Column(String, default="active")


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(String, ForeignKey("suppliers.supplier_id"), nullable=False)
    sku = Column(String, nullable=False)
    price = Column(Float, default=0.0)
    moq = Column(Integer, default=1)
    order_multiple = Column(Integer, default=1)
    max_qty = Column(Integer, default=1000)
    is_primary = Column(Boolean, default=False)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_id = Column(String, primary_key=True)
    supplier_id = Column(String, ForeignKey("suppliers.supplier_id"), nullable=False)
    sku = Column(String, nullable=False)
    node_id = Column(String, ForeignKey("fulfillment_nodes.node_id"), nullable=False)
    qty = Column(Integer, default=0)
    unit_price = Column(Float, default=0.0)
    status = Column(String, default="DRAFT")
    created_by = Column(String, default="agent")
    expected_arrival = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1)
    parent_po_id = Column(String, nullable=True)
    reason = Column(String, default="")
    approved = Column(Boolean, default=False)
    supplier_response = Column(String, default="pending")
    source_horizon_days = Column(Integer, default=14)


class Budget(Base):
    __tablename__ = "budgets"
    budget_id = Column(String, primary_key=True)
    category = Column(String, default="")
    node_id = Column(String, nullable=True)
    period = Column(String, default="2026-09")
    total = Column(Float, default=0.0)
    committed = Column(Float, default=0.0)
    remaining = Column(Float, default=0.0)


class Approval(Base):
    __tablename__ = "approvals"
    approval_id = Column(String, primary_key=True)
    po_id = Column(String, nullable=False)
    reason = Column(String, default="")
    risk_level = Column(String, default="medium")
    payload = Column(Text, default="{}")
    status = Column(String, default="PENDING")
    decided_by = Column(String, default="")
    decided_at = Column(DateTime, nullable=True)


class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(String, default="")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    run_id = Column(String, primary_key=True)
    scenario = Column(String, default="")
    input = Column(Text, default="{}")
    status = Column(String, default="started")
    final_decision = Column(String, default="")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class AgentStep(Base):
    __tablename__ = "agent_steps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    step_no = Column(Integer, default=0)
    type = Column(String, default="thought")
    payload = Column(Text, default="{}")
    latency_ms = Column(Integer, default=0)
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
