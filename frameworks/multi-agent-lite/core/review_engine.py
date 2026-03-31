from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from .acceptance_mapping import build_acceptance_evidence
from .task_expectations import get_task_expectations


class ReviewEngine:
    def evaluate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        acceptance: List[str] = task.get("acceptance", [])
        subtasks: List[Dict[str, Any]] = task.get("subtasks", [])
        task_type = task.get("task_type", "general")
        expectations = get_task_expectations(task_type)

        issues: List[str] = []
        quality_signals: List[str] = []
        blocking_gaps: List[str] = []
        residual_risks: List[str] = []
        acceptance_results: List[Dict[str, str]] = []

        if not subtasks:
            blocking_gaps.append("no subtasks available")

        task_level_deliverables = task.get("deliverables") or []
        delivery_summary = str(task.get("delivery_summary") or "").strip()
        delivery_changes = task.get("delivery_changes") or []
        delivery_evidence = task.get("delivery_evidence") or []
        task_level_risks = task.get("delivery_risks") or []

        for st in subtasks:
            if not st.get("assigned_model"):
                blocking_gaps.append(f"subtask {st.get('subtask_id')} missing assigned_model")

            if st.get("dispatch_status") != "completed":
                blocking_gaps.append(f"subtask {st.get('subtask_id')} not completed")

            result = st.get("result") or {}
            if not result:
                blocking_gaps.append(f"subtask {st.get('subtask_id')} missing result")
                continue

            if result.get("transport_error"):
                blocking_gaps.append(f"subtask {st.get('subtask_id')} transport_error")
            if result.get("protocol_error"):
                blocking_gaps.append(f"subtask {st.get('subtask_id')} protocol_error")
            if result.get("semantic_error"):
                blocking_gaps.append(f"subtask {st.get('subtask_id')} semantic_error")

            changes = result.get("changes") or []
            artifacts = result.get("artifacts") or []
            risks = result.get("risks") or []
            summary = str(result.get("summary") or "").strip()

            if st.get("assigned_role") in {"execution_code", "execution_general"}:
                if expectations.get("requires_meaningful_changes") and not changes:
                    blocking_gaps.append(f"subtask {st.get('subtask_id')} missing meaningful changes")
                if expectations.get("artifacts_preferred") and not changes and not artifacts:
                    blocking_gaps.append(f"subtask {st.get('subtask_id')} missing expected artifacts or changes")
                if not summary and not changes and not artifacts:
                    blocking_gaps.append(f"subtask {st.get('subtask_id')} produced no usable deliverable signal")

            for risk in risks:
                if risk and risk not in residual_risks:
                    residual_risks.append(risk)

        if not task_level_deliverables and task.get("artifacts"):
            task_level_deliverables = list(task.get("artifacts", []))

        if not delivery_summary:
            exec_summaries = []
            for st in subtasks:
                if st.get("assigned_role") in {"execution_code", "execution_general"}:
                    summary = str((st.get("result") or {}).get("summary") or "").strip()
                    if summary:
                        exec_summaries.append(summary)
            if exec_summaries:
                delivery_summary = " | ".join(exec_summaries[:3])

        goal = str(task.get("goal") or "").strip()
        goal_alignment_status = "unknown"
        goal_alignment_evidence = delivery_summary or "no delivery summary available"
        if delivery_summary:
            goal_alignment_status = "pass"
        else:
            goal_alignment_status = "fail"
            blocking_gaps.append("missing task-level delivery summary")

        if task_level_deliverables:
            quality_signals.append(f"task exposes {len(task_level_deliverables)} task-level deliverable(s)")
        else:
            blocking_gaps.append("missing task-level deliverables")

        acceptance_results.append({
            "item": f"address original goal: {goal}",
            "status": goal_alignment_status,
            "evidence": goal_alignment_evidence,
        })

        if acceptance:
            for item in acceptance:
                acceptance_results.append(build_acceptance_evidence(item, task))
            quality_signals.append(f"task defines {len(acceptance)} acceptance checkpoints")
        else:
            quality_signals.append("task has no explicit acceptance checkpoints")

        issues.extend(blocking_gaps)
        decision = "approved" if not issues else "changes_requested"
        next_action = "DONE" if decision == "approved" else "PLAN"
        delivery_status = "delivered" if delivery_summary and task_level_deliverables else "not_delivered"
        recommended_sendback_target = "none" if decision == "approved" else "execution"

        return {
            "review_id": f"REV-{uuid4().hex[:8].upper()}",
            "task_id": task["task_id"],
            "reviewer": "reviewer",
            "model": "o3",
            "decision": decision,
            "reasons": issues or ["deliverable addresses the task at current prototype standard"],
            "quality_signals": quality_signals,
            "acceptance_results": acceptance_results,
            "delivery_status": delivery_status,
            "blocking_gaps": blocking_gaps,
            "residual_risks": residual_risks,
            "recommended_sendback_target": recommended_sendback_target,
            "next_action": next_action,
        }
