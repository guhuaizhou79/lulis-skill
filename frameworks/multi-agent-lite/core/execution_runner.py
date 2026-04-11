from __future__ import annotations

from typing import Any, Dict, List


def _should_run_subtask(subtask: Dict[str, Any], rerun_only: bool) -> bool:
    if not rerun_only:
        return True
    if subtask.get("rerun_needed"):
        return True
    role = str(subtask.get("assigned_role") or "")
    return role.startswith("execution_") and subtask.get("dispatch_status") != "completed"


def execute_subtasks(task: Dict[str, Any], executor) -> Dict[str, Any]:
    executed: List[Dict[str, Any]] = []
    artifacts: List[str] = list(task.get("artifacts", []))
    rerun_only = bool(task.get("rerun_execution_only"))

    for subtask in task.get("subtasks", []):
        if not _should_run_subtask(subtask, rerun_only):
            executed.append(subtask)
            continue

        role = subtask.get("assigned_role", "")
        try:
            result = executor.run(role, subtask, task)
            has_primary_error = any([
                result.get("transport_error"),
                result.get("protocol_error"),
                result.get("semantic_error"),
            ])
            has_needs_input = bool(result.get("needs_input"))
            status = "needs_input" if has_needs_input else ("failed" if has_primary_error else "completed")
        except Exception as e:
            result = {
                "summary": f"executor failed unexpectedly: {str(e)}",
                "changes": [],
                "artifacts": [],
                "risks": [str(e)],
                "unknowns": [],
                "next_suggestion": "review orchestrator logs",
                "transport_error": True,
                "protocol_error": False,
                "semantic_error": False,
                "raw_excerpt": str(e)[:500],
            }
            status = "failed"

        updated = {
            **subtask,
            "dispatch_status": status,
            "result": result,
            "rerun_needed": False,
            "rerun_reason": None,
        }
        executed.append(updated)
        artifacts.extend(result.get("artifacts", []))

    task["subtasks"] = executed
    task["artifacts"] = artifacts
    task["rerun_execution_only"] = False
    return task
