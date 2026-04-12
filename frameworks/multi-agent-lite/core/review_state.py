from __future__ import annotations

from typing import Dict, Any


def apply_review(task: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
    task["last_review"] = review
    task.setdefault("reviews", []).append(review)

    decision = str(review.get("decision") or "").strip().lower()
    next_action = str(review.get("next_action") or "").strip().upper()
    recommended_sendback_target = str(review.get("recommended_sendback_target") or "").strip().lower()

    if decision == "approved":
        task["status"] = "DONE"
        task["rerun_execution_only"] = False
        return task

    if next_action == "BLOCKED" or recommended_sendback_target == "blocked":
        task["status"] = "BLOCKED"
        task["rerun_execution_only"] = False
        return task

    if next_action == "PLAN" or recommended_sendback_target == "manager":
        task["status"] = "PLAN"
        task["rerun_execution_only"] = False
        task["sendback_count"] = int(task.get("sendback_count", 0)) + 1
        return task

    if next_action == "EXECUTING" or recommended_sendback_target == "execution":
        task["status"] = "EXECUTING"
        task["rerun_execution_only"] = True
        task["sendback_count"] = int(task.get("sendback_count", 0)) + 1
        return task

    if next_action == "READY":
        task["status"] = "READY"
        task["rerun_execution_only"] = False
        return task

    if next_action == "FAILED":
        task["status"] = "FAILED"
        task["rerun_execution_only"] = False
        return task

    return task
