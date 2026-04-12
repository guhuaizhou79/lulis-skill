from __future__ import annotations

from typing import Any, Dict, List


def _derive_validation_policy(validation_records: List[Dict[str, Any]], risks: List[str], blockers: List[str], needs_input: List[str]) -> Dict[str, Any]:
    failed_surfaces = [str(x.get("surface") or "") for x in validation_records if str(x.get("status") or "") == "failed"]
    blocked_surfaces = [str(x.get("surface") or "") for x in validation_records if str(x.get("status") or "") == "blocked"]

    verdict_hint = "accepted"
    manager_action_hint = "finalize_or_merge"
    change_disposition_hint = "keep_for_review"

    if blockers or needs_input or blocked_surfaces:
        verdict_hint = "blocked"
        manager_action_hint = "request_input_or_unblock"
        change_disposition_hint = "review_then_revert_or_keep"
    elif any(surface in {"syntax", "import"} for surface in failed_surfaces):
        verdict_hint = "needs_replan"
        manager_action_hint = "sendback_with_replan"
        change_disposition_hint = "revert_suggested"
    elif any(surface in {"unit", "project_command"} for surface in failed_surfaces):
        verdict_hint = "needs_replan"
        manager_action_hint = "sendback_with_replan"
        change_disposition_hint = "keep_for_review"

    return {
        "failed_surfaces": failed_surfaces,
        "blocked_surfaces": blocked_surfaces,
        "verdict_hint": verdict_hint,
        "manager_action_hint": manager_action_hint,
        "change_disposition_hint": change_disposition_hint,
    }


def _build_review_packet(*, files_changed: List[str] | None = None, target_files: List[str] | None = None, tests_run: List[str] | None = None, test_results: List[str] | None = None, validation_records: List[Dict[str, Any]] | None = None, risks: List[str] | None = None, blockers: List[str] | None = None, needs_input: List[str] | None = None) -> Dict[str, Any]:
    files_changed = [str(x) for x in (files_changed or []) if str(x).strip()]
    target_files = [str(x) for x in (target_files or []) if str(x).strip()]
    tests_run = [str(x) for x in (tests_run or []) if str(x).strip()]
    test_results = [str(x) for x in (test_results or []) if str(x).strip()]
    validation_records = [x for x in (validation_records or []) if isinstance(x, dict)]
    risks = [str(x) for x in (risks or []) if str(x).strip()]
    blockers = [str(x) for x in (blockers or []) if str(x).strip()]
    needs_input = [str(x) for x in (needs_input or []) if str(x).strip()]

    blocked = bool(blockers or needs_input or any("blocked" in x.lower() for x in test_results))
    failed = any("failed" in x.lower() for x in test_results)
    policy = _derive_validation_policy(validation_records, risks, blockers, needs_input)
    if blocked:
        verdict = "blocked"
    elif failed:
        verdict = str(policy.get("verdict_hint") or "needs_replan")
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
        manager_action = str(policy.get("manager_action_hint") or "sendback_with_replan")
    elif verdict == "blocked":
        manager_action = str(policy.get("manager_action_hint") or "request_input_or_unblock")

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
        "validation_records": validation_records,
        "validation_policy": policy,
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


def _derive_retry_narrowing_hints(*, target_files: List[str], validation_records: List[Dict[str, Any]], validation_policy: Dict[str, Any], edit_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
    failed_surfaces = [str(x) for x in (validation_policy.get("failed_surfaces") or []) if str(x).strip()]
    top_files = [str(x) for x in (target_files or []) if str(x).strip()][:3]
    symbol_hits: List[str] = []
    for item in (edit_plan or [])[:5]:
        ctx = item.get("context") or {}
        for symbol in (ctx.get("goal_symbol_hits") or []):
            value = str(symbol).strip()
            if value and value not in symbol_hits:
                symbol_hits.append(value)

    validation_focus = failed_surfaces[:3]
    scope_level = "broad"
    if symbol_hits:
        scope_level = "symbol"
    elif top_files:
        scope_level = "file"
    elif validation_focus:
        scope_level = "validation_surface"

    return {
        "scope_level": scope_level,
        "target_files": top_files,
        "target_symbols": symbol_hits[:5],
        "validation_focus": validation_focus,
        "suggested_actions": [
            "narrow the next run to the smallest failing scope",
            "preserve validation coverage for previously failing surfaces",
        ],
    }


def build_coding_result_packet(packet: Dict[str, Any], *, summary: str, files_changed: List[str] | None = None, target_files: List[str] | None = None, deliverables: List[str] | None = None, repo_scan: Dict[str, Any] | None = None, edit_plan: List[Dict[str, Any]] | None = None, draft_artifacts: List[str] | None = None, tests_run: List[str] | None = None, test_results: List[str] | None = None, validation_records: List[Dict[str, Any]] | None = None, risks: List[str] | None = None, blockers: List[str] | None = None, needs_input: List[str] | None = None, recommended_next_step: str = "") -> Dict[str, Any]:
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
        validation_records=validation_records,
        risks=risks,
        blockers=blockers,
        needs_input=needs_input,
    )
    validation_policy = dict(review_packet.get("validation_policy") or {})
    retry_narrowing_hints = _derive_retry_narrowing_hints(
        target_files=target_files,
        validation_records=[dict(x) for x in (validation_records or []) if isinstance(x, dict)],
        validation_policy=validation_policy,
        edit_plan=list(edit_plan or []),
    )
    review_packet["retry_narrowing_hints"] = retry_narrowing_hints
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
        "validation_records": [dict(x) for x in (validation_records or []) if isinstance(x, dict)],
        "validation_policy": validation_policy,
        "retry_narrowing_hints": retry_narrowing_hints,
        "risks": risks,
        "blockers": blockers,
        "needs_input": needs_input,
        "review_packet": review_packet,
        "recommended_next_step": recommended_next_step,
    }
