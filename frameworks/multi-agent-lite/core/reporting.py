from __future__ import annotations

from typing import Any, Dict, List


def summarize_dispatches(subtasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total": len(subtasks),
        "by_role": {
            role: len([s for s in subtasks if s.get("assigned_role") == role])
            for role in sorted({s.get("assigned_role") for s in subtasks})
        },
        "models": [
            {
                "subtask_id": s.get("subtask_id"),
                "role": s.get("assigned_role"),
                "model": s.get("assigned_model"),
            }
            for s in subtasks
        ],
    }
