from __future__ import annotations

from typing import Any, Dict, List


def execute_subtasks(task: Dict[str, Any], executor) -> Dict[str, Any]:
    executed: List[Dict[str, Any]] = []
    artifacts: List[str] = list(task.get("artifacts", []))

    for subtask in task.get("subtasks", []):
        role = subtask.get("assigned_role", "")
        try:
            result = executor.run(role, subtask, task)
            status = "completed"
        except Exception as e:
            result = {
                "summary": f"executor failed unexpectedly: {str(e)}",
                "changes": [],
                "artifacts": [],
                "risks": [str(e)],
                "unknowns": [],
                "next_suggestion": "review orchestrator logs",
                "executor_error": True,
            }
            status = "failed"

        updated = {
            **subtask,
            "dispatch_status": status,
            "result": result,
        }
        executed.append(updated)
        artifacts.extend(result.get("artifacts", []))

    task["subtasks"] = executed
    task["artifacts"] = artifacts
    return task
