from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from .task_expectations import get_task_expectations


class ReviewEngine:
    def evaluate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        acceptance: List[str] = task.get("acceptance", [])
        subtasks: List[Dict[str, Any]] = task.get("subtasks", [])
        task_type = task.get("task_type", "general")
        expectations = get_task_expectations(task_type)
        issues: List[str] = []
        quality_signals: List[str] = []

        if not subtasks:
            issues.append("no subtasks available")

        for st in subtasks:
            if not st.get("assigned_model"):
                issues.append(f"subtask {st.get('subtask_id')} missing assigned_model")
            if st.get("dispatch_status") != "completed":
                issues.append(f"subtask {st.get('subtask_id')} not completed")
            result = st.get("result") or {}
            if not result:
                issues.append(f"subtask {st.get('subtask_id')} missing result")
                continue
            if result.get("parse_error"):
                issues.append(f"subtask {st.get('subtask_id')} parse_error")
            if result.get("executor_error"):
                issues.append(f"subtask {st.get('subtask_id')} executor_error")

            changes = result.get("changes") or []
            artifacts = result.get("artifacts") or []
            risks = result.get("risks") or []

            if st.get("assigned_role") in {"execution_code", "execution_general"}:
                if expectations.get("requires_meaningful_changes") and not changes:
                    issues.append(f"subtask {st.get('subtask_id')} missing meaningful changes")
                if expectations.get("artifacts_preferred") and not changes and not artifacts:
                    issues.append(f"subtask {st.get('subtask_id')} missing expected artifacts or changes")
                if not risks:
                    quality_signals.append(f"subtask {st.get('subtask_id')} reported no explicit risks")

        if acceptance:
            quality_signals.append(f"task defines {len(acceptance)} acceptance checkpoints")
        else:
            quality_signals.append("task has no explicit acceptance checkpoints")

        decision = "approved" if not issues else "changes_requested"
        next_action = "DONE" if decision == "approved" else "PLAN"

        return {
            "review_id": f"REV-{uuid4().hex[:8].upper()}",
            "task_id": task["task_id"],
            "reviewer": "reviewer",
            "model": "o3",
            "decision": decision,
            "reasons": issues or [f"meets {len(acceptance)} acceptance checkpoints at current prototype stage"],
            "quality_signals": quality_signals,
            "next_action": next_action,
        }
