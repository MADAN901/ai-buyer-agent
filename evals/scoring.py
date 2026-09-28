from __future__ import annotations

from typing import Any


def score_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passing = sum(1 for item in results if item.get("status") == "completed")
    return {
        "total_cases": total,
        "passing_cases": passing,
        "pass_rate": round((passing / total) * 100, 2) if total else 0.0,
        "rubric": [
            "decision correctness",
            "information gathering",
            "constraint compliance",
            "action appropriateness",
            "validation performed",
        ],
    }
