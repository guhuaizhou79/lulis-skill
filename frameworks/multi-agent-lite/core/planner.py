from __future__ import annotations

from typing import Any, Dict, List


def build_plan(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    goal = task.get("goal", "")
    task_type = task.get("task_type", "general")

    base: List[Dict[str, Any]] = [
        {
            "subtask_id": "SUB-RESEARCH-01",
            "title": "gather context and constraints",
            "assigned_role": "research",
            "status": "pending",
            "objective": f"collect the facts, context, and constraints for: {goal}",
        },
        {
            "subtask_id": "SUB-EXEC-01",
            "title": "produce first deliverable",
            "assigned_role": "execution_code" if task_type in {"code", "framework_design", "automation"} else "execution_general",
            "status": "pending",
            "objective": f"produce the first workable deliverable for: {goal}",
        },
        {
            "subtask_id": "SUB-REVIEW-01",
            "title": "review against acceptance",
            "assigned_role": "reviewer",
            "status": "pending",
            "objective": "review outputs against acceptance criteria and decide approve / changes requested",
        },
    ]
    return base
