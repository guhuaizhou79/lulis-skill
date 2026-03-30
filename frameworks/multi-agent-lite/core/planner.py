from __future__ import annotations

from typing import Any, Dict, List


STRICT_TASK_TYPES = {"automation", "framework_design"}
RESEARCH_HEAVY_TASK_TYPES = {"code", "automation", "framework_design"}


def select_planning_profile(task: Dict[str, Any]) -> str:
    task_type = task.get("task_type", "general")
    acceptance = task.get("acceptance", []) or []
    constraints = task.get("constraints", []) or []
    priority = task.get("priority", "normal")

    if task_type in STRICT_TASK_TYPES or priority == "high":
        return "research_execute_review_strict"
    if task_type in RESEARCH_HEAVY_TASK_TYPES or acceptance or constraints:
        return "research_execute_review"
    return "direct_review"



def build_plan(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    goal = task.get("goal", "")
    task_type = task.get("task_type", "general")
    profile = select_planning_profile(task)

    execution_role = "execution_code" if task_type in {"code", "framework_design", "automation"} else "execution_general"
    subtasks: List[Dict[str, Any]] = []

    if profile in {"research_execute_review", "research_execute_review_strict"}:
        subtasks.append(
            {
                "subtask_id": "SUB-RESEARCH-01",
                "title": "gather context and constraints",
                "assigned_role": "research",
                "status": "pending",
                "objective": f"collect the facts, context, and constraints for: {goal}",
                "planning_profile": profile,
            }
        )

    subtasks.append(
        {
            "subtask_id": "SUB-EXEC-01",
            "title": "produce first deliverable",
            "assigned_role": execution_role,
            "status": "pending",
            "objective": f"produce the first workable deliverable for: {goal}",
            "planning_profile": profile,
        }
    )

    review_objective = "review outputs against acceptance criteria and decide approve / changes requested"
    if profile == "research_execute_review_strict":
        review_objective = (
            "strictly review outputs against acceptance criteria, unresolved risks, and delivery readiness; "
            "decide approve / changes requested"
        )

    subtasks.append(
        {
            "subtask_id": "SUB-REVIEW-01",
            "title": "review against acceptance",
            "assigned_role": "reviewer",
            "status": "pending",
            "objective": review_objective,
            "planning_profile": profile,
        }
    )

    return subtasks
