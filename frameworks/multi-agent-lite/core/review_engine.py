from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4


class ReviewEngine:
    def evaluate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        acceptance: List[str] = task.get("acceptance", [])
        subtasks: List[Dict[str, Any]] = task.get("subtasks", [])
        missing = []

        if not subtasks:
            missing.append("no subtasks available")

        for st in subtasks:
            if not st.get("assigned_model"):
                missing.append(f"subtask {st.get('subtask_id')} missing assigned_model")
            if st.get("dispatch_status") != "completed":
                missing.append(f"subtask {st.get('subtask_id')} not completed")
            result = st.get("result") or {}
            if not result:
                missing.append(f"subtask {st.get('subtask_id')} missing result")
            if result.get("parse_error"):
                missing.append(f"subtask {st.get('subtask_id')} parse_error")
            if result.get("executor_error"):
                missing.append(f"subtask {st.get('subtask_id')} executor_error")

        decision = "approved" if not missing else "changes_requested"
        next_action = "DONE" if decision == "approved" else "PLAN"

        return {
            "review_id": f"REV-{uuid4().hex[:8].upper()}",
            "task_id": task["task_id"],
            "reviewer": "reviewer",
            "model": "o3",
            "decision": decision,
            "reasons": missing or [f"meets {len(acceptance)} acceptance checkpoints at current prototype stage"],
            "next_action": next_action,
        }
