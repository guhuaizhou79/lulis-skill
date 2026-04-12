from __future__ import annotations

from typing import Any, Dict, List


def _build_review_packet(*, files_changed: List[str] | None = None, target_files: List[str] | None = None, tests_run: List[str] | None = None, test_results: List[str] | None = None, risks: List[str] | None = None, blockers: List[str] | None = None, needs_input: List[str] | None = None) -> Dict[str, Any]:
    files_changed = [str(x) for x in (files_changed or []) if str(x).strip()]
    target_files = [str(x) for x in (target_files or []) if str(x).strip()]
    tests_run = [str(x) for x in (tests_run or []) if str(x).strip()]
    test_results = [str(x) for x in (test_results or []) if str(x).strip()]
    risks = [str(x) for x in (risks or []) if str(x).strip()]
    blockers = [str(x) for x in (blockers or []) if str(x).strip()]
    needs_input = [str(x) for x in (needs_input or []) if str(x).strip()]

    blocked = bool(blockers or needs_input or any("blocked" in x.lower() for x in test_results))
    failed = any("failed" in x.lower() for x in test_results)
    if blocked:
        verdict = "blocked"
    elif failed:
        verdict = "needs_replan"
    elif files_changed or tests_run:
        verdict = "accepted"
    else:
        verdict = "review_needed"

    scope = "none"
    if len(target_files) > 1 or len(files_changed) > 1:
        scope = "multi_file"
    elif len(target_files) == 1 or len(files_changed) == 1:
        scope = "single_file"

    confidence = "low"
    if verdict == "accepted" and tests_run and not failed and not blocked:
        confidence = "medium"
    if verdict == "accepted" and tests_run and not risks and len(files_changed) >= 1:
        confidence = "high"
    if verdict in {"blocked", "needs_replan"}:
        confidence = "medium"

    manager_action = "review"
    if verdict == "accepted":
        manager_action = "finalize_or_merge"
    elif verdict == "needs_replan":
        manager_action = "sendback_with_replan"
    elif verdict == "blocked":
        manager_action = "request_input_or_unblock"

    rollback_hint = "no file changes applied"
    if files_changed:
        rollback_hint = f"revert touched files if downstream review rejects this run: {files_changed[:5]}"

    return {
        "verdict": verdict,
        "confidence": confidence,
        "change_scope": scope,
        "files_changed_count": len(files_changed),
        "targets_considered": target_files,
        "tests_considered": tests_run,
        "risk_count": len(risks),
        "blocking_reasons": blockers + needs_input,
        "rollback_hint": rollback_hint,
        "manager_action_suggestion": manager_action,
    }


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
    blockers = [reason]
    needs_input = [reason]
    return {
        "status": "blocked",
        "summary": reason,
        "repo_path": packet.get("repo_path") or "",
        "files_changed": [],
        "target_files": [],
        "deliverables": [],
        "repo_scan": {},
        "edit_plan": [],
        "draft_artifacts": [],
        "tests_run": [],
        "test_results": [],
        "risks": [],
        "blockers": blockers,
        "needs_input": needs_input,
        "review_packet": _build_review_packet(
            files_changed=[],
            target_files=[],
            tests_run=[],
            test_results=[],
            risks=[],
            blockers=blockers,
            needs_input=needs_input,
        ),
        "recommended_next_step": "clarify missing repo_path / goal / scope",
    }


def build_coding_result_packet(packet: Dict[str, Any], *, summary: str, files_changed: List[str] | None = None, target_files: List[str] | None = None, deliverables: List[str] | None = None, repo_scan: Dict[str, Any] | None = None, edit_plan: List[Dict[str, Any]] | None = None, draft_artifacts: List[str] | None = None, tests_run: List[str] | None = None, test_results: List[str] | None = None, risks: List[str] | None = None, blockers: List[str] | None = None, needs_input: List[str] | None = None, recommended_next_step: str = "") -> Dict[str, Any]:
    blockers = [str(x) for x in (blockers or []) if str(x).strip()]
    needs_input = [str(x) for x in (needs_input or []) if str(x).strip()]
    files_changed = [str(x) for x in (files_changed or []) if str(x).strip()]
    target_files = [str(x) for x in (target_files or []) if str(x).strip()]
    tests_run = [str(x) for x in (tests_run or []) if str(x).strip()]
    test_results = [str(x) for x in (test_results or []) if str(x).strip()]
    risks = [str(x) for x in (risks or []) if str(x).strip()]
    status = "success"
    if blockers or needs_input:
        status = "blocked"
    review_packet = _build_review_packet(
        files_changed=files_changed,
        target_files=target_files,
        tests_run=tests_run,
        test_results=test_results,
        risks=risks,
        blockers=blockers,
        needs_input=needs_input,
    )
    return {
        "status": status,
        "summary": summary,
        "repo_path": packet.get("repo_path") or "",
        "files_changed": files_changed,
        "target_files": target_files,
        "deliverables": [str(x) for x in (deliverables or []) if str(x).strip()],
        "repo_scan": dict(repo_scan or {}),
        "edit_plan": list(edit_plan or []),
        "draft_artifacts": [str(x) for x in (draft_artifacts or []) if str(x).strip()],
        "tests_run": tests_run,
        "test_results": test_results,
        "risks": risks,
        "blockers": blockers,
        "needs_input": needs_input,
        "review_packet": review_packet,
        "recommended_next_step": recommended_next_step,
    }
