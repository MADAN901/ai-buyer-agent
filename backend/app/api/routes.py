from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.db.database import SessionLocal
from app.agent.orchestrator import Orchestrator
from app.models.models import AgentRun, AgentStep, Approval, PurchaseOrder
from app.schemas.schemas import ApprovalDecision, ScenarioFixture

router = APIRouter(prefix="/api")

SCENARIOS = [
    ScenarioFixture(id="S1-A", title="Accept", description="Healthy demand with valid coverage and budget.", expected_outcome="Accept"),
    ScenarioFixture(id="S1-B", title="Modify over-order", description="Open POs cover part of demand; reorder should be reduced.", expected_outcome="Modify"),
    ScenarioFixture(id="S1-C", title="Modify storage", description="Need exceeds storage; split or postpone.", expected_outcome="Modify"),
    ScenarioFixture(id="S1-D", title="Modify budget", description="Budget cap requires lower quantity.", expected_outcome="Modify"),
    ScenarioFixture(id="S1-E", title="Reject", description="Incoming stock already covers the horizon.", expected_outcome="Reject"),
    ScenarioFixture(id="S1-F", title="Investigate", description="Forecast stale or low-accuracy; backfill with history.", expected_outcome="Investigate_Further"),
    ScenarioFixture(id="S2-A", title="Recover partial supplier", description="Supplier confirms partial; accept without new PO.", expected_outcome="Modify"),
    ScenarioFixture(id="S2-B", title="Recover alternate supplier", description="Supplier partial, stock risk remains; source alternative.", expected_outcome="Modify"),
    ScenarioFixture(id="S2-C", title="Escalate", description="All paths fail; escalate with briefing.", expected_outcome="Escalate"),
]

orchestrator = Orchestrator()


@router.get("/scenarios")
def get_scenarios() -> list[ScenarioFixture]:
    return SCENARIOS


@router.post("/agent/run")
def run_agent(payload: dict[str, Any]) -> dict[str, Any]:
    scenario_id = payload.get("scenario_id", "S1-A")
    return orchestrator.run_scenario(scenario_id, payload)


@router.get("/agent/runs")
def list_runs() -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(AgentRun).order_by(AgentRun.started_at.desc()).all()
        return [
            {
                "run_id": row.run_id,
                "scenario": row.scenario,
                "status": row.status,
                "final_decision": row.final_decision,
                "started_at": row.started_at.isoformat() if row.started_at else None,
            }
            for row in rows
        ]
    finally:
        db.close()


@router.get("/agent/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        run = db.query(AgentRun).filter_by(run_id=run_id).one_or_none()
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")

        steps = db.query(AgentStep).filter_by(run_id=run_id).order_by(AgentStep.step_no.asc()).all()
        return {
            "run_id": run.run_id,
            "scenario": run.scenario,
            "status": run.status,
            "final_decision": run.final_decision,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "steps": [
                {
                    "step_no": step.step_no,
                    "type": step.type,
                    "payload": json.loads(step.payload) if step.payload else {},
                    "latency_ms": step.latency_ms,
                    "tokens": step.tokens,
                }
                for step in steps
            ],
        }
    finally:
        db.close()


@router.get("/agent/runs/{run_id}/stream")
def stream_run(run_id: str):
    def event_stream():
        db = SessionLocal()
        try:
            run = db.query(AgentRun).filter_by(run_id=run_id).one_or_none()
            if run is None:
                yield 'data: {"event": "error", "message": "Run not found"}\n\n'
                return

            yield f"data: {json.dumps({'event': 'run', 'run_id': run.run_id, 'scenario': run.scenario, 'status': run.status, 'final_decision': run.final_decision})}\n\n"

            steps = db.query(AgentStep).filter_by(run_id=run_id).order_by(AgentStep.step_no.asc()).all()
            for step in steps:
                payload = json.loads(step.payload) if step.payload else {}
                yield f"data: {json.dumps({'event': 'step', 'step_no': step.step_no, 'type': step.type, 'payload': payload})}\n\n"

            yield f"data: {json.dumps({'event': 'done', 'run_id': run.run_id})}\n\n"
        finally:
            db.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/approvals")
def get_approvals() -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(Approval).all()
        return [{"approval_id": row.approval_id, "po_id": row.po_id, "status": row.status, "risk_level": row.risk_level, "reason": row.reason} for row in rows]
    finally:
        db.close()


@router.post("/approvals/{approval_id}/approve")
def approve_approval(approval_id: str, payload: ApprovalDecision):
    return {"ok": True, "approval_id": approval_id, "status": "approved" if payload.approve else "rejected"}


@router.post("/approvals/{approval_id}/reject")
def reject_approval(approval_id: str, payload: ApprovalDecision):
    return {"ok": True, "approval_id": approval_id, "status": "rejected"}


@router.get("/pos")
def list_pos() -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(PurchaseOrder).all()
        return [{"po_id": row.po_id, "sku": row.sku, "node_id": row.node_id, "supplier_id": row.supplier_id, "qty": row.qty, "status": row.status} for row in rows]
    finally:
        db.close()


@router.get("/pos/{po_id}")
def get_po(po_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        row = db.query(PurchaseOrder).filter_by(po_id=po_id).one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="PO not found")
        return {"po_id": row.po_id, "sku": row.sku, "node_id": row.node_id, "supplier_id": row.supplier_id, "qty": row.qty, "status": row.status, "version": row.version}
    finally:
        db.close()


@router.get("/data/{kind}")
def get_data(kind: str) -> dict[str, Any]:
    return {"kind": kind, "items": []}


@router.post("/data/mutate")
def mutate_data(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "payload": payload}


@router.post("/chaos")
def set_chaos(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "chaos": payload.get("enabled", False)}


@router.post("/eval/run")
def eval_run():
    from evals.run import run_eval_suite
    return run_eval_suite()


@router.get("/eval/results")
def eval_results():
    return {"results": []}


@router.post("/seed/reset")
def reset_seed():
    from app.seed.__main__ import seed_database
    seed_database()
    return {"ok": True}
