from app.agent.orchestrator import Orchestrator
from app.db.database import SessionLocal
from app.models.models import AgentRun


def test_run_scenario_persists_single_agent_run():
    orchestrator = Orchestrator()
    result = orchestrator.run_scenario("S1-A", {"scenario_id": "S1-A", "recommended_qty": 800, "supplier_id": "SUP-1", "node_id": "NODE-1"})

    db = SessionLocal()
    try:
        run = db.query(AgentRun).filter(AgentRun.run_id == result["run_id"]).one()
        assert run.status == "completed"
        assert run.final_decision == result["final_decision"]
    finally:
        db.close()
