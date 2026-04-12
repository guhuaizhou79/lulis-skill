from __future__ import annotations

from typing import Any, Dict, List


def build_coding_task_packet(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_kind": "coding_execution",
        "title": str(payload.get("title") or "untitled coding task"),
        "goal": str(payload.get("goal") or ""),
        "repo_path": str(payload.get("repo_path") or ""),
        "files_of_interest": [str(x) for x in (payload.get("files_of_interest") or []) if str(x).strip()],
        "constraints": [str(x) for x in (payload.get("constraints") or []) if str(x).strip()],
        "acceptance": [str(x) for x in (payload.get("acceptance") or []) if str(x).strip()],
        "allowed_actions": [str(x) for x in (payload.get("allowed_actions") or ["read", "edit", "validate"]) if str(x).strip()],
        "validation_expectations": [str(x) for x in (payload.get("validation_expectations") or []) if str(x).strip()],
    }


def build_empty_coding_result(packet: Dict[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "status": "blocked",
        "summary": reason,
        "repo_path": packet.get("repo_path") or "",
        "files_changed": [],
        "target_files": [],
        "deliverables": [],
        "repo_scan": {},
        "edit_plan": [],
        "tests_run": [],
        "test_results": [],
        "risks": [],
        "blockers": [reason],
        "needs_input": [reason],
        "recommended_next_step": "clarify missing repo_path / goal / scope",
    }


def build_coding_result_packet(packet: Dict[str, Any], *, summary: str, files_changed: List[str] | None = None, target_files: List[str] | None = None, deliverables: List[str] | None = None, repo_scan: Dict[str, Any] | None = None, edit_plan: List[Dict[str, Any]] | None = None, tests_run: List[str] | None = None, test_results: List[str] | None = None, risks: List[str] | None = None, blockers: List[str] | None = None, needs_input: List[str] | None = None, recommended_next_step: str = "") -> Dict[str, Any]:
    blockers = [str(x) for x in (blockers or []) if str(x).strip()]
    needs_input = [str(x) for x in (needs_input or []) if str(x).strip()]
    status = "success"
    if blockers or needs_input:
        status = "blocked"
    return {
        "status": status,
        "summary": summary,
        "repo_path": packet.get("repo_path") or "",
        "files_changed": [str(x) for x in (files_changed or []) if str(x).strip()],
        "target_files": [str(x) for x in (target_files or []) if str(x).strip()],
        "deliverables": [str(x) for x in (deliverables or []) if str(x).strip()],
        "repo_scan": dict(repo_scan or {}),
        "edit_plan": list(edit_plan or []),
        "tests_run": [str(x) for x in (tests_run or []) if str(x).strip()],
        "test_results": [str(x) for x in (test_results or []) if str(x).strip()],
        "risks": [str(x) for x in (risks or []) if str(x).strip()],
        "blockers": blockers,
        "needs_input": needs_input,
        "recommended_next_step": recommended_next_step,
    }
