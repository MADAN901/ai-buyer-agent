"""Seed the SQLite database with realistic scenario fixtures."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.db.database import Base, SessionLocal, engine
from app.models.models import (
    Approval,
    Budget,
    Forecast,
    FulfillmentNode,
    Inventory,
    Policy,
    Product,
    PurchaseOrder,
    SalesHistory,
    Supplier,
    SupplierProduct,
)


def seed_database() -> None:
    settings = get_settings()
    db_dir = Path(settings.database_url.replace("sqlite:///", "", 1))
    if db_dir.exists() or str(db_dir).endswith(".db"):
        db_dir = db_dir.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(Product).delete()
        db.query(FulfillmentNode).delete()
        db.query(Inventory).delete()
        db.query(SalesHistory).delete()
        db.query(Forecast).delete()
        db.query(Supplier).delete()
        db.query(SupplierProduct).delete()
        db.query(PurchaseOrder).delete()
        db.query(Budget).delete()
        db.query(Approval).delete()
        db.query(Policy).delete()

        products = [
            Product(sku="SKU-100", name="Citrus Juice 1L", category="beverages", unit_cost=13.5, unit_volume_m3=0.02, shelf_life_days=21, is_perishable=True),
            Product(sku="SKU-101", name="Salad Mix 300g", category="fresh", unit_cost=4.2, unit_volume_m3=0.015, shelf_life_days=5, is_perishable=True),
            Product(sku="SKU-102", name="Greek Yogurt 500g", category="dairy", unit_cost=6.0, unit_volume_m3=0.02, shelf_life_days=10, is_perishable=True),
            Product(sku="SKU-200", name="Rice 5kg", category="dry_goods", unit_cost=18.0, unit_volume_m3=0.04, shelf_life_days=365, is_perishable=False),
            Product(sku="SKU-201", name="Pasta 1kg", category="dry_goods", unit_cost=2.7, unit_volume_m3=0.03, shelf_life_days=365, is_perishable=False),
            Product(sku="SKU-300", name="Baby Wipes", category="household", unit_cost=2.1, unit_volume_m3=0.01, shelf_life_days=365, is_perishable=False),
        ]
        db.add_all(products)

        nodes = [
            FulfillmentNode(node_id="NODE-1", name="Downtown Dark Store", city="New York", storage_capacity_m3=180.0, storage_used_m3=70.0, cold_chain_capacity_m3=60.0, dry_goods_capacity_m3=120.0),
            FulfillmentNode(node_id="NODE-2", name="Brooklyn DC", city="Brooklyn", storage_capacity_m3=220.0, storage_used_m3=95.0, cold_chain_capacity_m3=80.0, dry_goods_capacity_m3=140.0),
            FulfillmentNode(node_id="NODE-3", name="Queens Hub", city="Queens", storage_capacity_m3=200.0, storage_used_m3=110.0, cold_chain_capacity_m3=70.0, dry_goods_capacity_m3=130.0),
        ]
        db.add_all(nodes)

        inventory_rows = [
            Inventory(sku="SKU-100", node_id="NODE-1", on_hand=120, reserved=20, damaged=5, updated_at=datetime.utcnow()),
            Inventory(sku="SKU-100", node_id="NODE-2", on_hand=90, reserved=10, damaged=0, updated_at=datetime.utcnow()),
            Inventory(sku="SKU-200", node_id="NODE-2", on_hand=80, reserved=15, damaged=0, updated_at=datetime.utcnow()),
            Inventory(sku="SKU-101", node_id="NODE-3", on_hand=60, reserved=5, damaged=3, updated_at=datetime.utcnow()),
            Inventory(sku="SKU-300", node_id="NODE-1", on_hand=200, reserved=30, damaged=0, updated_at=datetime.utcnow()),
        ]
        db.add_all(inventory_rows)

        base_date = datetime.utcnow() - timedelta(days=90)
        sales = []
        for day in range(90):
            d = base_date + timedelta(days=day)
            sales.append(SalesHistory(sku="SKU-100", node_id="NODE-1", date=d, units_sold=14 + (day % 7), promo_flag=(day % 12 == 0), stockout_flag=(day % 18 == 0)))
            sales.append(SalesHistory(sku="SKU-100", node_id="NODE-2", date=d, units_sold=10 + (day % 5), promo_flag=False, stockout_flag=False))
            sales.append(SalesHistory(sku="SKU-200", node_id="NODE-2", date=d, units_sold=9 + ((day * 2) % 7), promo_flag=(day % 17 == 0), stockout_flag=False))
            sales.append(SalesHistory(sku="SKU-101", node_id="NODE-3", date=d, units_sold=12 + (day % 6), promo_flag=False, stockout_flag=(day % 20 == 0)))
        db.add_all(sales)

        forecasts = [
            Forecast(sku="SKU-100", node_id="NODE-1", horizon_days=14, expected_daily_demand=12.0, model_version="v4", generated_at=datetime.utcnow() - timedelta(days=12), mape=0.16),
            Forecast(sku="SKU-100", node_id="NODE-2", horizon_days=14, expected_daily_demand=9.0, model_version="v4", generated_at=datetime.utcnow() - timedelta(days=2), mape=0.10),
            Forecast(sku="SKU-200", node_id="NODE-2", horizon_days=14, expected_daily_demand=9.0, model_version="v3", generated_at=datetime.utcnow() - timedelta(days=21), mape=0.32),
            Forecast(sku="SKU-101", node_id="NODE-3", horizon_days=14, expected_daily_demand=11.0, model_version="v4", generated_at=datetime.utcnow() - timedelta(days=1), mape=0.09),
        ]
        db.add_all(forecasts)

        suppliers = [
            Supplier(supplier_id="SUP-1", name="North Valley Foods", lead_time_days=4, lead_time_std_days=2, moq_units=200, order_multiple=25, price_per_unit=12.8, fill_rate_pct=0.97, on_time_pct=0.96, payment_terms="NET14", status="active"),
            Supplier(supplier_id="SUP-2", name="Metro Fresh Co.", lead_time_days=6, lead_time_std_days=3, moq_units=150, order_multiple=50, price_per_unit=13.1, fill_rate_pct=0.91, on_time_pct=0.89, payment_terms="NET30", status="active"),
            Supplier(supplier_id="SUP-3", name="Harbor Wholesale", lead_time_days=9, lead_time_std_days=4, moq_units=120, order_multiple=10, price_per_unit=14.8, fill_rate_pct=0.84, on_time_pct=0.83, payment_terms="NET14", status="active"),
            Supplier(supplier_id="SUP-4", name="Delta Supply", lead_time_days=12, lead_time_std_days=5, moq_units=300, order_multiple=50, price_per_unit=11.2, fill_rate_pct=0.72, on_time_pct=0.7, payment_terms="NET45", status="blocked"),
        ]
        db.add_all(suppliers)

        supplier_products = [
            SupplierProduct(supplier_id="SUP-1", sku="SKU-100", price=12.8, moq=200, order_multiple=25, max_qty=600, is_primary=True),
            SupplierProduct(supplier_id="SUP-2", sku="SKU-100", price=13.1, moq=150, order_multiple=50, max_qty=700, is_primary=False),
            SupplierProduct(supplier_id="SUP-3", sku="SKU-100", price=14.8, moq=120, order_multiple=10, max_qty=500, is_primary=False),
            SupplierProduct(supplier_id="SUP-4", sku="SKU-100", price=11.2, moq=300, order_multiple=50, max_qty=800, is_primary=False),
            SupplierProduct(supplier_id="SUP-1", sku="SKU-200", price=18.0, moq=100, order_multiple=25, max_qty=600, is_primary=True),
            SupplierProduct(supplier_id="SUP-2", sku="SKU-200", price=19.5, moq=80, order_multiple=10, max_qty=500, is_primary=False),
        ]
        db.add_all(supplier_products)

        purchase_orders = [
            PurchaseOrder(po_id="PO-100", supplier_id="SUP-1", sku="SKU-100", node_id="NODE-1", qty=500, unit_price=12.8, status="SENT", created_by="agent", expected_arrival=datetime.utcnow() + timedelta(days=4), version=1, reason="initial forecast cover", supplier_response="confirmed", approved=True),
            PurchaseOrder(po_id="PO-200", supplier_id="SUP-1", sku="SKU-200", node_id="NODE-2", qty=250, unit_price=18.0, status="CONFIRMED", created_by="agent", expected_arrival=datetime.utcnow() + timedelta(days=6), version=1, reason="stock cover", supplier_response="confirmed", approved=True),
        ]
        db.add_all(purchase_orders)

        budgets = [
            Budget(budget_id="B-1", category="fresh", node_id="NODE-1", period="2026-09", total=12000.0, committed=5600.0, remaining=6400.0),
            Budget(budget_id="B-2", category="dry_goods", node_id="NODE-2", period="2026-09", total=9000.0, committed=4200.0, remaining=4800.0),
            Budget(budget_id="B-3", category="fresh", node_id="NODE-3", period="2026-09", total=10000.0, committed=3500.0, remaining=6500.0),
        ]
        db.add_all(budgets)

        policies = [
            Policy(name="max_auto_approve_value", value="5000"),
            Policy(name="max_cover_days", value="21"),
            Policy(name="min_safety_days", value="3"),
            Policy(name="max_supplier_concentration", value="0.7"),
            Policy(name="max_agent_iterations", value="3"),
            Policy(name="max_tool_calls", value="40"),
        ]
        db.add_all(policies)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
    print("Database seeded with realistic fixtures.")
