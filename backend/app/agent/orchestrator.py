from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.agent.prompts import PROMPT
from app.core.replenishment import compute_replenishment
from app.db.database import SessionLocal
from app.llm.providers import MockLLMProvider
from app.models.models import AgentRun, AgentStep, Policy
from app.policy.engine import PolicyEngine
from app.tools.tools import (
    compute_replenishment_tool,
    create_purchase_order,
    get_budget,
    get_demand_forecast,
    get_inventory,
    get_open_purchase_orders,
    get_policies,
    get_sales_history,
    get_storage_capacity,
    get_supplier_terms,
    list_alternate_suppliers,
    request_human_approval,
)


class Orchestrator:
    def __init__(self, provider=None):
        self.provider = provider or MockLLMProvider()
        self.policy_engine = PolicyEngine()

    def run_scenario(self, scenario_id: str, input_data: dict[str, Any] | None = None) -> dict[str, Any]:
        run_id = f"RUN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{abs(hash((scenario_id, json.dumps(input_data or {}, sort_keys=True)))) % 10000}"
        db = SessionLocal()
        try:
            run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
            if run is None:
                run = AgentRun(run_id=run_id, scenario=scenario_id, input=json.dumps(input_data or {}), status="running")
                db.add(run)
            else:
                run.scenario = scenario_id
                run.input = json.dumps(input_data or {})
                run.status = "running"
                run.final_decision = ""
            db.commit()
        finally:
            db.close()

        steps = []
        context = {
            "scenario": scenario_id,
            "recommended_qty": input_data.get("recommended_qty", 800) if input_data else 800,
            "supplier_id": input_data.get("supplier_id") if input_data else "SUP-1",
            "node_id": input_data.get("node_id") if input_data else "NODE-1",
        }

        actions = [
            ("inventory", lambda: get_inventory(context["node_id"].split("NODE-")[-1] if False else "SKU-100", context["node_id"])),
            ("forecast", lambda: get_demand_forecast("SKU-100", context["node_id"])),
            ("open_pos", lambda: get_open_purchase_orders("SKU-100", context["node_id"])),
            ("budget", lambda: get_budget(node_id=context["node_id"])),
            ("storage", lambda: get_storage_capacity(context["node_id"])),
            ("policies", lambda: get_policies()),
        ]

        for idx, (name, fn) in enumerate(actions, start=1):
            payload = fn()
            steps.append({"step_no": idx, "type": "observation", "payload": payload, "latency_ms": 10, "tokens": 0})

        plan = self.provider.plan(scenario_id, context)
        steps.append({"step_no": len(steps) + 1, "type": "decision", "payload": plan.model_dump(), "latency_ms": 10, "tokens": 0})

        policy_result = self.policy_engine.validate(
            qty=plan.quantity or 0,
            supplier_id=plan.supplier_id,
            node_id=plan.node_id,
            unit_price=10.0,
            budget_remaining=5000.0,
            storage_free_m3=30.0,
            volume_m3=plan.quantity * 0.02 if plan.quantity else 0,
            supplier_status="active",
            supplier_moq=1,
            order_multiple=1,
            supplier_max_qty=None,
            auto_approve_limit=5000.0,
        )
        steps.append({"step_no": len(steps) + 1, "type": "validation", "payload": policy_result.model_dump(), "latency_ms": 10, "tokens": 0})

        result = {
            "run_id": run_id,
            "status": "completed",
            "scenario": scenario_id,
            "final_decision": plan.decision,
            "steps": steps,
            "prompt": PROMPT,
        }

        db = SessionLocal()
        try:
            existing_run = db.query(AgentRun).filter(AgentRun.run_id == run_id).one_or_none()
            if existing_run is None:
                existing_run = AgentRun(run_id=run_id, scenario=scenario_id, input=json.dumps(input_data or {}), status="completed", final_decision=plan.decision)
                db.add(existing_run)
            else:
                existing_run.scenario = scenario_id
                existing_run.input = json.dumps(input_data or {})
                existing_run.status = "completed"
                existing_run.final_decision = plan.decision
                existing_run.ended_at = datetime.utcnow()

            for step_no, step in enumerate(steps, start=1):
                db.add(AgentStep(run_id=run_id, step_no=step_no, type=step["type"], payload=json.dumps(step["payload"]), latency_ms=step["latency_ms"], tokens=step["tokens"]))
            db.commit()
        finally:
            db.close()
        return result
