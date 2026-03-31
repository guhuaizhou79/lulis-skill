from __future__ import annotations

from __future__ import annotations

from typing import Any, Dict, List

from .task_expectations import get_task_expectations


STRICT_TASK_TYPES = {"automation", "framework_design"}
RESEARCH_HEAVY_TASK_TYPES = {"code", "automation", "framework_design"}


PLANNING_PROFILES: Dict[str, Dict[str, Any]] = {
    "direct_review": {
        "include_research": False,
        "strict_review": False,
        "execution_title": "produce first deliverable",
    },
    "research_execute_review": {
        "include_research": True,
        "strict_review": False,
        "execution_title": "produce first deliverable",
    },
    "research_execute_review_strict": {
        "include_research": True,
        "strict_review": True,
        "execution_title": "produce delivery-ready candidate",
    },
}


def select_planning_profile(task: Dict[str, Any]) -> str:
    task_type = task.get("task_type", "general")
    acceptance = task.get("acceptance", []) or []
    constraints = task.get("constraints", []) or []
    priority = task.get("priority", "normal")

    if task_type in STRICT_TASK_TYPES or priority in {"high", "critical"}:
        return "research_execute_review_strict"
    if task_type in RESEARCH_HEAVY_TASK_TYPES or acceptance or constraints:
        return "research_execute_review"
    return "direct_review"


def _profile_config(profile: str) -> Dict[str, Any]:
    if profile not in PLANNING_PROFILES:
        raise KeyError(f"unknown planning profile: {profile}")
    return PLANNING_PROFILES[profile]


def build_plan(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    goal = task.get("goal", "")
    task_type = task.get("task_type", "general")
    acceptance = task.get("acceptance", []) or []
    constraints = task.get("constraints", []) or []
    profile = select_planning_profile(task)
    profile_cfg = _profile_config(profile)
    expectations = get_task_expectations(task_type)
    output_shape = expectations.get("output_shape", "general_deliverable")

    execution_role = expectations["expected_execution_role"]
    subtasks: List[Dict[str, Any]] = []

    if profile_cfg["include_research"]:
        research_objective = f"collect the facts, context, and constraints for: {goal}"
        if acceptance or constraints:
            research_objective += (
                f" | acceptance={acceptance or []}"
                f" | constraints={constraints or []}"
            )
        subtasks.append(
            {
                "subtask_id": "SUB-RESEARCH-01",
                "title": "gather context and constraints",
                "assigned_role": "research",
                "status": "pending",
                "objective": research_objective,
                "planning_profile": profile,
            }
        )

    execution_objective = f"produce the first workable deliverable for: {goal}"
    if profile_cfg["strict_review"]:
        execution_objective = f"produce a delivery-ready candidate for: {goal}"
    if acceptance or constraints:
        execution_objective += (
            f" | acceptance={acceptance or []}"
            f" | constraints={constraints or []}"
        )
    execution_objective += f" | output_shape={output_shape}"

    subtasks.append(
        {
            "subtask_id": "SUB-EXEC-01",
            "title": profile_cfg["execution_title"],
            "assigned_role": execution_role,
            "status": "pending",
            "objective": execution_objective,
            "planning_profile": profile,
        }
    )

    review_objective = "review outputs against acceptance criteria and decide approve / changes requested"
    if profile_cfg["strict_review"] or expectations.get("strict_review"):
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
