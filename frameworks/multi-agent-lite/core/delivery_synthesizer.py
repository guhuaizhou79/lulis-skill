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


def _pick_evidence_refs(evidence_map: List[Dict[str, Any]], max_refs: int = 5) -> List[str]:
    refs: List[str] = []
    for item in evidence_map:
        if item.get("state") != "active":
            continue
        subtask_id = str(item.get("subtask_id") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if subtask_id and summary:
            refs.append(f"{subtask_id}: {summary[:120]}")
        for artifact in item.get("artifacts") or []:
            refs.append(str(artifact))
        if len(refs) >= max_refs:
            break
    return _unique(refs)[:max_refs]


def _collect_needs_input(subtasks: List[Dict[str, Any]]) -> List[str]:
    needs: List[str] = []
    for st in subtasks:
        result = st.get("result") or {}
        for item in result.get("needs_input") or []:
            value = str(item or "").strip()
            if value:
                needs.append(value)
    return _unique(needs)


def _derive_result_status(task: Dict[str, Any], needs_input: List[str]) -> str:
    if needs_input:
        return "blocked"
    if task.get("delivery_status") == "delivered":
        return "success"
    if task.get("delivery_status") in {"assembled", "not_delivered"}:
        return "changes_requested"
    return "blocked"


def _build_writeback_recommendation(task: Dict[str, Any]) -> Dict[str, Any]:
    return task.get("writeback_hint") or {"level": 0, "targets": []}


def _build_evidence_entry(subtask_id: str, role: str, result: Dict[str, Any], state: str, round_id: int | None = None) -> Dict[str, Any]:
    summary = str(result.get("summary") or "").strip()
    changes = _unique(list(result.get("changes") or []))
    artifacts = _unique(list(result.get("artifacts") or []))
    risks = _unique(list(result.get("risks") or []))
    entry = {
        "subtask_id": subtask_id,
        "role": role,
        "summary": summary,
        "changes": changes,
        "artifacts": artifacts,
        "risks": risks,
        "evidence": _unique(([summary] if summary else []) + changes + artifacts),
        "state": state,
    }
    if round_id is not None:
        entry["round"] = round_id
    stale_reason = result.get("stale_reason")
    if stale_reason:
        entry["stale_reason"] = stale_reason
    return entry


def synthesize_delivery(task: Dict[str, Any]) -> Dict[str, Any]:
    subtasks: List[Dict[str, Any]] = task.get("subtasks", []) or []

    deliverables: List[str] = []
    delivery_summary_parts: List[str] = []
    delivery_changes: List[str] = []
    residual_risks: List[str] = []
    evidence_map: List[Dict[str, Any]] = []
    internal_evidence_map: List[Dict[str, Any]] = []
    deliverable_candidates: List[str] = []

    for st in subtasks:
        role = st.get("assigned_role")
        result = st.get("result") or {}
        if role not in EXECUTION_ROLES:
            continue

        subtask_id = str(st.get("subtask_id") or "")
        stale_result = st.get("stale_result") or {}
        stale_round = st.get("superseded_by_rerun_round")
        if stale_result:
            internal_evidence_map.append(_build_evidence_entry(subtask_id, role, stale_result, state="stale", round_id=stale_round))

        active_entry = _build_evidence_entry(subtask_id, role, result, state="active")
        evidence_map.append(active_entry)
        internal_evidence_map.append(active_entry)

        summary = active_entry["summary"]
        changes = active_entry["changes"]
        artifacts = active_entry["artifacts"]
        risks = active_entry["risks"]

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

    delivery_summary = " | ".join(_unique(delivery_summary_parts)[:3])
    deliverables = _unique(deliverables)
    delivery_changes = _unique(delivery_changes)
    deliverable_candidates = _unique(deliverable_candidates)

    if not deliverables and delivery_changes:
        deliverables = delivery_changes[:3]

    delivery_status = "assembled" if (deliverables or delivery_summary or delivery_changes) else "not_delivered"
    if delivery_summary and deliverables:
        delivery_status = "delivered"

    needs_input = _collect_needs_input(subtasks)

    task["deliverables"] = deliverables
    task["delivery_summary"] = delivery_summary
    task["delivery_changes"] = delivery_changes
    task["delivery_risks"] = _unique(residual_risks)
    task["delivery_evidence"] = evidence_map
    task["delivery_internal_evidence"] = internal_evidence_map
    task["deliverable_candidates"] = deliverable_candidates
    task["delivery_status"] = delivery_status
    task["task_result_packet"] = {
        "status": _derive_result_status(task, needs_input),
        "summary": delivery_summary,
        "deliverables": deliverables,
        "changes": delivery_changes,
        "risks": task["delivery_risks"],
        "needs_input": needs_input,
        "evidence_refs": _pick_evidence_refs(evidence_map),
        "writeback_recommendation": _build_writeback_recommendation(task),
    }
    return task
