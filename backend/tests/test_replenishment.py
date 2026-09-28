from app.core.replenishment import compute_replenishment


def test_compute_replenishment_basic():
    result = compute_replenishment(
        sku="SKU-100",
        node_id="NODE-1",
        on_hand=120,
        reserved=20,
        damaged=5,
        inbound_po_qty=80,
        daily_demand=10,
        lead_time_days=7,
        review_days=3,
        service_level=0.95,
        supplier_moq=50,
        order_multiple=25,
        max_qty=500,
        budget_limit=1000,
        storage_limit=200,
        max_cover_days=21,
        unit_cost=14.0,
        unit_volume=0.02,
    )
    assert result["feasible_qty"] >= 0
    assert result["cost"] >= 0
    assert "binding_constraints" in result


def test_compute_replenishment_binding_constraints():
    result = compute_replenishment(
        sku="SKU-200",
        node_id="NODE-2",
        on_hand=5,
        reserved=0,
        damaged=0,
        inbound_po_qty=0,
        daily_demand=40,
        lead_time_days=10,
        review_days=3,
        service_level=0.95,
        supplier_moq=100,
        order_multiple=50,
        max_qty=150,
        budget_limit=2000,
        storage_limit=200,
        max_cover_days=14,
        unit_cost=20.0,
        unit_volume=0.03,
    )
    assert "moq" in result["binding_constraints"] or "max_cover_days" in result["binding_constraints"] or "order_multiple" in result["binding_constraints"]
