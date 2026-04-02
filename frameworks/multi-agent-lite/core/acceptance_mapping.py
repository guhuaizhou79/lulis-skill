from __future__ import annotations

from typing import Any, Dict, List


def _norm(value: str) -> List[str]:
    tokens = []
    for part in (value or "").lower().replace("_", " ").replace("-", " ").split():
        token = part.strip()
        if token:
            tokens.append(token)
    return tokens


def _is_meaningful_token(token: str) -> bool:
    token = (token or "").strip().lower()
    if len(token) <= 2:
        return False
    if token in {
        "the", "and", "for", "with", "that", "this", "from", "into", "then", "than",
        "task", "result", "review", "output", "returns", "return", "state", "file", "files",
        "exact", "given", "first", "basis", "checks", "check", "can", "all"
    }:
        return False
    return True


def _filtered_token_set(value: str) -> set[str]:
    return {token for token in _norm(value) if _is_meaningful_token(token)}


def build_acceptance_evidence(
    item: str,
    task: Dict[str, Any],
    executor_acceptance_checks: List[Dict[str, Any]] | None = None,
    failure_override: bool = False,
) -> Dict[str, Any]:
    item_tokens = _filtered_token_set(item)
    evidence_hits: List[str] = []
    task_level_hits: List[str] = []

    candidates: List[str] = []
    candidates.extend([str(x) for x in task.get("deliverables") or []])
    candidates.extend([str(x) for x in task.get("delivery_changes") or []])
    candidates.extend([str(x) for x in task.get("deliverable_candidates") or []])
    summary = str(task.get("delivery_summary") or "").strip()
    if summary:
        candidates.append(summary)

    deduped_candidates: List[str] = []
    seen = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_candidates.append(normalized)

    for candidate in deduped_candidates:
        candidate_tokens = _filtered_token_set(candidate)
        if not candidate_tokens or not item_tokens:
            continue
        overlap = item_tokens.intersection(candidate_tokens)
        if len(overlap) >= 2:
            task_level_hits.append(candidate)

    matched_executor_checks: List[Dict[str, Any]] = []
    for check in executor_acceptance_checks or []:
        check_item = str(check.get("item") or "").strip()
        if not check_item:
            continue
        check_tokens = _filtered_token_set(check_item)
        if item_tokens and check_tokens and item_tokens == check_tokens:
            matched_executor_checks.append(check)

    if matched_executor_checks:
        for check in matched_executor_checks:
            evidence = str(check.get("evidence") or "").strip()
            status = str(check.get("status") or "unknown").strip() or "unknown"
            label = f"executor_check[{status}]"
            if evidence:
                evidence_hits.append(f"{label}: {evidence}")
            else:
                evidence_hits.append(label)
    elif task_level_hits:
        evidence_hits.extend(task_level_hits[:2])

    derived_status = "pass" if matched_executor_checks else ("partial" if task_level_hits else "unknown")
    if matched_executor_checks:
        statuses = [str(check.get("status") or "unknown").strip() or "unknown" for check in matched_executor_checks]
        if any(status == "fail" for status in statuses):
            derived_status = "fail"
        elif any(status == "partial" for status in statuses):
            derived_status = "partial"
        elif any(status == "pass" for status in statuses):
            derived_status = "pass"
        else:
            derived_status = "unknown"

    evidence_text = "; ".join(evidence_hits[:3]) if evidence_hits else "no task-level evidence collected"
    if failure_override and derived_status == "pass":
        derived_status = "partial"
        if evidence_text != "no task-level evidence collected":
            evidence_text = f"failure_override: upstream execution not yet reliable | {evidence_text}"
        else:
            evidence_text = "failure_override: upstream execution not yet reliable"

    return {
        "item": item,
        "status": derived_status,
        "evidence": evidence_text,
    }
