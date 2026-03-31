from __future__ import annotations

from typing import Any, Dict, List


EXECUTION_ROLES = {"execution_code", "execution_general"}


def _unique(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def synthesize_delivery(task: Dict[str, Any]) -> Dict[str, Any]:
    subtasks: List[Dict[str, Any]] = task.get("subtasks", []) or []

    deliverables: List[str] = list(task.get("artifacts", []) or [])
    delivery_summary_parts: List[str] = []
    delivery_changes: List[str] = []
    residual_risks: List[str] = []
    evidence_map: List[Dict[str, Any]] = []
    deliverable_candidates: List[str] = []

    for st in subtasks:
        role = st.get("assigned_role")
        result = st.get("result") or {}
        if role not in EXECUTION_ROLES:
            continue

        summary = str(result.get("summary") or "").strip()
        changes = _unique(list(result.get("changes") or []))
        artifacts = _unique(list(result.get("artifacts") or []))
        risks = _unique(list(result.get("risks") or []))
        subtask_id = str(st.get("subtask_id") or "")

        if summary:
            delivery_summary_parts.append(summary)
            deliverable_candidates.append(summary)
        for item in artifacts:
            if item not in deliverables:
                deliverables.append(item)
            deliverable_candidates.append(item)
        for item in changes:
            if item not in delivery_changes:
                delivery_changes.append(item)
            deliverable_candidates.append(item)
        for item in risks:
            if item not in residual_risks:
                residual_risks.append(item)

        evidence_map.append({
            "subtask_id": subtask_id,
            "role": role,
            "summary": summary,
            "changes": changes,
            "artifacts": artifacts,
            "risks": risks,
            "evidence": _unique(([summary] if summary else []) + changes + artifacts),
        })

    delivery_summary = " | ".join(_unique(delivery_summary_parts)[:3])
    deliverables = _unique(deliverables)
    delivery_changes = _unique(delivery_changes)
    deliverable_candidates = _unique(deliverable_candidates)

    if not deliverables and delivery_changes:
        deliverables = delivery_changes[:3]

    delivery_status = "assembled" if (deliverables or delivery_summary or delivery_changes) else "not_delivered"

    task["deliverables"] = deliverables
    task["delivery_summary"] = delivery_summary
    task["delivery_changes"] = delivery_changes
    task["delivery_risks"] = _unique(residual_risks)
    task["delivery_evidence"] = evidence_map
    task["deliverable_candidates"] = deliverable_candidates
    task["delivery_status"] = delivery_status
    return task
