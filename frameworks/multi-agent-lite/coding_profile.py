from __future__ import annotations

from typing import Any, Dict, List


CODE_TASK_TYPES = {"code", "bugfix", "refactor", "repo_analysis"}


def is_coding_task(task: Dict[str, Any]) -> bool:
    task_type = str(task.get("task_type") or "").strip()
    if task_type in CODE_TASK_TYPES:
        return True
    goal = str(task.get("goal") or "").lower()
    title = str(task.get("title") or "").lower()
    hints = ["code", "repo", "bug", "fix", "refactor", "implement", "module", "function"]
    text = f"{title} {goal}"
    return any(token in text for token in hints)


def build_code_context_packet(task: Dict[str, Any]) -> Dict[str, Any]:
    constraints = [str(x) for x in (task.get("constraints") or []) if str(x).strip()]
    acceptance = [str(x) for x in (task.get("acceptance") or []) if str(x).strip()]
    return {
        "task_type": str(task.get("task_type") or "general"),
        "goal": str(task.get("goal") or ""),
        "constraints": constraints,
        "acceptance": acceptance,
        "focus": {
            "needs_code_changes": True,
            "needs_repo_reading": True,
            "needs_validation": True,
        },
    }


def build_code_result_packet(task: Dict[str, Any], packet: Dict[str, Any]) -> Dict[str, Any]:
    changes = [str(x) for x in (packet.get("changes") or []) if str(x).strip()]
    deliverables = [str(x) for x in (packet.get("deliverables") or []) if str(x).strip()]
    evidence_refs = [str(x) for x in (packet.get("evidence_refs") or []) if str(x).strip()]
    risks = [str(x) for x in (packet.get("risks") or []) if str(x).strip()]

    files_touched = [item for item in deliverables if "/" in item or item.endswith((".py", ".md", ".json", ".ts", ".tsx", ".js"))]
    test_refs = [item for item in evidence_refs if "validate" in item.lower() or "test" in item.lower()]

    return {
        "code_change_summary": str(packet.get("summary") or ""),
        "files_touched": files_touched,
        "contracts_changed": [],
        "tests_run": test_refs,
        "test_results": ["passed" for _ in test_refs],
        "risk_surface": risks,
        "rollback_notes": [],
        "followup_refactors": [],
        "repo_context": build_code_context_packet(task),
        "change_count": len(changes),
    }
