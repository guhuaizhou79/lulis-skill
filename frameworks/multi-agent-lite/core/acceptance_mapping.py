from __future__ import annotations

from typing import Any, Dict, List


def _norm(value: str) -> List[str]:
    tokens = []
    for part in (value or "").lower().replace("_", " ").replace("-", " ").split():
        token = part.strip()
        if token:
            tokens.append(token)
    return tokens


def build_acceptance_evidence(item: str, task: Dict[str, Any]) -> Dict[str, Any]:
    item_tokens = set(_norm(item))
    evidence_hits: List[str] = []

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
        candidate_tokens = set(_norm(candidate))
        if not candidate_tokens:
            continue
        if item_tokens and item_tokens.intersection(candidate_tokens):
            evidence_hits.append(candidate)

    if not evidence_hits and deduped_candidates:
        evidence_hits = deduped_candidates[:2]

    status = "pass" if evidence_hits else "unknown"
    evidence_text = "; ".join(evidence_hits[:3]) if evidence_hits else "no task-level evidence collected"
    return {
        "item": item,
        "status": status,
        "evidence": evidence_text,
    }
