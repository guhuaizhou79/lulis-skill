from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json


def _outer_runtime_dir(root: Path) -> Path:
    path = root / "runtime" / "outer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _compact_list(values: List[Any]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in values:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def build_writeback_plan(outer_result: Dict[str, Any]) -> Dict[str, Any]:
    packet = outer_result.get("task_result_packet") or {}
    policy = outer_result.get("writeback_policy") or {}
    hint = outer_result.get("writeback_hint") or {"level": 0, "targets": []}
    normalized_status = str(outer_result.get("normalized_status") or "in_progress")
    run_id = str(outer_result.get("run_id") or "UNKNOWN")

    recommended_targets = _compact_list(policy.get("recommended_targets") or hint.get("targets") or [])
    deliverables = _compact_list(packet.get("deliverables") or [])
    changes = _compact_list(packet.get("changes") or [])
    risks = _compact_list(packet.get("risks") or [])
    needs_input = _compact_list(packet.get("needs_input") or [])
    evidence_refs = _compact_list(packet.get("evidence_refs") or [])

    actions: List[Dict[str, Any]] = []

    if policy.get("should_write_summary"):
        actions.append({
            "kind": "summary_stub",
            "target": "working-summary",
            "reason": "successful result is worth summary-layer convergence",
            "status": "planned",
        })

    if policy.get("should_write_state"):
        actions.append({
            "kind": "state_stub",
            "target": "current-state",
            "reason": f"normalized status is {normalized_status}, so outer state may need sync",
            "status": "planned",
        })

    if policy.get("should_write_memory"):
        actions.append({
            "kind": "memory_stub",
            "target": "memory",
            "reason": "writeback hint reached durable-memory threshold",
            "status": "planned",
        })

    return {
        "run_id": run_id,
        "advisory_only": True,
        "final_authority": "outer_framework",
        "normalized_status": normalized_status,
        "summary": str(packet.get("summary") or ""),
        "recommended_targets": recommended_targets,
        "actions": actions,
        "inputs": {
            "deliverables": deliverables,
            "changes": changes,
            "risks": risks,
            "needs_input": needs_input,
            "evidence_refs": evidence_refs,
        },
    }


def materialize_writeback_stub(root: Path, writeback_plan: Dict[str, Any]) -> Dict[str, Any]:
    runtime_dir = _outer_runtime_dir(root)
    run_id = str(writeback_plan.get("run_id") or "UNKNOWN")
    path = runtime_dir / f"writeback-{run_id}.json"
    path.write_text(json.dumps(writeback_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    row = {
        "run_id": run_id,
        "artifact": str(path),
        "kind": "writeback_stub",
        "advisory_only": bool(writeback_plan.get("advisory_only", True)),
        "action_count": len(writeback_plan.get("actions") or []),
        "normalized_status": writeback_plan.get("normalized_status"),
    }
    with (runtime_dir / "writeback_registry.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "path": str(path),
        "action_count": row["action_count"],
        "registry": str(runtime_dir / "writeback_registry.jsonl"),
    }
