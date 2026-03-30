from __future__ import annotations

from typing import Any, Dict


class MockExecutor:
    def run(self, role: str, subtask: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        objective = subtask.get("objective", "")
        if role == "research":
            return {
                "summary": f"researched context for: {task.get('title')}",
                "changes": ["collected constraints", "summarized goal"],
                "artifacts": [],
                "risks": [],
                "unknowns": [],
                "next_suggestion": f"handoff to next role with objective: {objective}",
            }
        if role in {"execution_code", "execution_general"}:
            return {
                "summary": f"produced draft deliverable for: {task.get('title')}",
                "changes": ["built first-pass output"],
                "artifacts": [],
                "risks": ["still mock execution"],
                "unknowns": [],
                "next_suggestion": "send to reviewer",
            }
        if role == "reviewer":
            return {
                "summary": f"review prepared for: {task.get('title')}",
                "changes": ["checked assigned models and dispatch readiness"],
                "artifacts": [],
                "risks": [],
                "unknowns": [],
                "next_suggestion": "apply review decision",
            }
        return {
            "summary": f"no-op executor result for role {role}",
            "changes": [],
            "artifacts": [],
            "risks": [],
            "unknowns": ["unknown role"],
            "next_suggestion": "inspect routing",
        }
