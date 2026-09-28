from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent.orchestrator import Orchestrator
from app.seed.__main__ import seed_database

seed_database()

SCENARIOS = [
    {"id": "S1-A", "input": {"scenario_id": "S1-A", "recommended_qty": 800, "supplier_id": "SUP-1", "node_id": "NODE-1"}},
    {"id": "S1-B", "input": {"scenario_id": "S1-B", "recommended_qty": 800, "supplier_id": "SUP-1", "node_id": "NODE-1"}},
    {"id": "S1-C", "input": {"scenario_id": "S1-C", "recommended_qty": 800, "supplier_id": "SUP-1", "node_id": "NODE-1"}},
    {"id": "S1-D", "input": {"scenario_id": "S1-D", "recommended_qty": 800, "supplier_id": "SUP-1", "node_id": "NODE-1"}},
    {"id": "S1-E", "input": {"scenario_id": "S1-E", "recommended_qty": 800, "supplier_id": "SUP-1", "node_id": "NODE-1"}},
    {"id": "S1-F", "input": {"scenario_id": "S1-F", "recommended_qty": 800, "supplier_id": "SUP-1", "node_id": "NODE-1"}},
    {"id": "S2-A", "input": {"scenario_id": "S2-A", "recommended_qty": 500, "supplier_id": "SUP-2", "node_id": "NODE-2"}},
    {"id": "S2-B", "input": {"scenario_id": "S2-B", "recommended_qty": 500, "supplier_id": "SUP-2", "node_id": "NODE-2"}},
    {"id": "S4-D", "input": {"scenario_id": "S4-D", "recommended_qty": 1000, "supplier_id": "SUP-4", "node_id": "NODE-1"}},
]


def run_eval_suite() -> dict:
    orchestrator = Orchestrator()
    results = []
    for case in SCENARIOS:
        result = orchestrator.run_scenario(case["id"], case["input"])
        results.append({"id": case["id"], "decision": result["final_decision"], "status": result["status"]})
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "latest.json"
    out_path.write_text(json.dumps({"results": results}, indent=2))
    return {"results": results, "path": str(out_path)}


if __name__ == "__main__":
    print(run_eval_suite())
