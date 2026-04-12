from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4
from datetime import datetime, timezone
import json
import sys


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from outer_adapter import choose_route, run_adapter
from writeback_stub import build_writeback_plan, materialize_writeback_stub
from coding_profile import is_coding_task, build_code_result_packet
from coding_executor import materialize_coding_run


DIRECT_TASK_TYPES = {"choice_answering", "path_lookup", "fact_lookup"}
LIGHT_TASK_TYPES = {"general", "config_authoring"}


def _default_task_result_packet(summary: str, *, changes: List[str] | None = None, risks: List[str] | None = None, needs_input: List[str] | None = None, writeback_level: int = 0, writeback_targets: List[str] | None = None) -> Dict[str, Any]:
    return {
        "status": "success" if not (needs_input or []) else "blocked",
        "summary": summary,
        "deliverables": [],
        "changes": list(changes or []),
        "risks": list(risks or []),
        "needs_input": list(needs_input or []),
        "evidence_refs": [],
        "writeback_recommendation": {
            "level": writeback_level,
            "targets": list(writeback_targets or []),
        },
    }


def _build_direct_raw_task(payload: Dict[str, Any], summary: str) -> Dict[str, Any]:
    return {
        "task_id": None,
        "route": "direct",
        "title": payload.get("title"),
        "goal": payload.get("goal"),
        "task_type": payload.get("task_type"),
        "priority": payload.get("priority", "normal"),
        "status": "DONE",
        "orchestration_mode": "direct",
        "task_result_packet": _default_task_result_packet(summary),
        "writeback_hint": {"level": 0, "targets": []},
        "degrade_history": [],
        "sendback_count": 0,
        "artifact_lifecycle": [],
    }


def _build_light_raw_task(payload: Dict[str, Any], summary: str) -> Dict[str, Any]:
    return {
        "task_id": None,
        "route": "light_role_check",
        "title": payload.get("title"),
        "goal": payload.get("goal"),
        "task_type": payload.get("task_type"),
        "priority": payload.get("priority", "normal"),
        "status": "DONE",
        "orchestration_mode": "light_role_check",
        "task_result_packet": _default_task_result_packet(
            summary,
            changes=["performed lightweight structured pass"],
        ),
        "writeback_hint": {"level": 0, "targets": []},
        "degrade_history": [],
        "sendback_count": 0,
        "artifact_lifecycle": [],
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _outer_runtime_dir(root: Path) -> Path:
    path = root / "runtime" / "outer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sendback_runtime_dir(root: Path) -> Path:
    path = _outer_runtime_dir(root) / "sendback"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_sendback_history(root: Path, task_key: str) -> List[Dict[str, Any]]:
    path = _sendback_runtime_dir(root) / f"{task_key}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def _store_sendback_history(root: Path, task_key: str, rows: List[Dict[str, Any]]) -> str:
    path = _sendback_runtime_dir(root) / f"{task_key}.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _append_registry_row(root: Path, row: Dict[str, Any]) -> None:
    path = _outer_runtime_dir(root) / "registry.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _task_sendback_key(payload: Dict[str, Any], route_result: Dict[str, Any]) -> str:
    repo_path = str(payload.get("repo_path") or "").strip().lower().replace("/", "-")
    title = str(payload.get("title") or payload.get("goal") or "task").strip().lower().replace(" ", "-")
    base = f"{repo_path}--{title}" if repo_path else title
    safe = "".join(ch for ch in base if ch.isalnum() or ch in {"-", "_"})[:120]
    return safe or "task"


def _dedupe_strings(values: List[Any]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in values:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def build_next_executor_payload(payload: Dict[str, Any], route_result: Dict[str, Any]) -> Dict[str, Any] | None:
    sendback_packet = route_result.get("manager_sendback_packet") or {}
    if not sendback_packet:
        return None

    verdict = str(sendback_packet.get("verdict") or "")
    coding_exec = route_result.get("coding_executor_result") or {}
    review_packet = coding_exec.get("review_packet") or {}
    why = sendback_packet.get("why") or {}
    blockers = _dedupe_strings((why.get("blockers") or []) + (review_packet.get("blocking_reasons") or []))
    needs_input = _dedupe_strings(why.get("needs_input") or [])
    risks = _dedupe_strings((why.get("risks") or []) + (coding_exec.get("risks") or []))
    test_results = _dedupe_strings(why.get("test_results") or coding_exec.get("test_results") or [])
    files_changed = _dedupe_strings(sendback_packet.get("files_changed") or coding_exec.get("files_changed") or [])
    history = [x for x in (route_result.get("sendback_history") or []) if isinstance(x, dict)]
    prior_verdicts = [str(x.get("verdict") or "").strip() for x in history if str(x.get("verdict") or "").strip()]
    repeated_same_verdict = len(prior_verdicts) >= 2 and len(set(prior_verdicts[-2:])) == 1

    next_constraints = _dedupe_strings(list(payload.get("constraints") or []) + [
        "Stay within coding-executor scope; do not become a second manager/controller.",
        "Use review/sendback signals to refine the next run, not to expand orchestration ownership.",
        "Prefer narrower, validation-backed edits over wider speculative changes.",
    ])
    next_acceptance = list(payload.get("acceptance") or [])
    next_allowed_actions = list(payload.get("allowed_actions") or [])
    next_validation_commands = list(payload.get("validation_commands") or [])
    next_files = list(payload.get("files_of_interest") or [])

    retry_notes: List[str] = []
    if blockers:
        retry_notes.append("Resolve blockers or collect missing input before re-running broad edits.")
    if test_results:
        retry_notes.append("Address the last failed/blocked validation signals before adding new scope.")
    if files_changed:
        retry_notes.append(f"Re-check touched files first: {files_changed[:5]}")
    if repeated_same_verdict:
        retry_notes.append("Repeated same-verdict sendback detected; tighten scope and avoid repeating the prior attempt.")

    next_goal_parts = [str(payload.get("goal") or "").strip()]
    if verdict == "needs_replan":
        next_goal_parts.append("Replan the coding run narrowly around the last failed validation/review signals.")
    elif verdict == "blocked":
        next_goal_parts.append("Unblock missing inputs or reduce scope before retrying coding execution.")
    if retry_notes:
        next_goal_parts.append(" ".join(retry_notes))
    next_goal = " ".join(part for part in next_goal_parts if part).strip()

    if sendback_packet.get("next_executor_payload_hints", {}).get("tighten_target_files") and files_changed:
        normalized_files: List[str] = []
        repo_path = str(payload.get("repo_path") or "").strip()
        repo_prefix = repo_path.rstrip("/") + "/" if repo_path else ""
        for item in files_changed:
            rel = str(item)
            if repo_prefix and rel.startswith(repo_prefix):
                rel = rel[len(repo_prefix):]
            normalized_files.append(rel)
        next_files = _dedupe_strings(normalized_files + next_files)

    if sendback_packet.get("next_executor_payload_hints", {}).get("tighten_allowed_actions"):
        next_allowed_actions = [x for x in next_allowed_actions if x in {"read", "replace", "validate"}]
        if not next_allowed_actions:
            next_allowed_actions = ["read", "replace", "validate"]

    if sendback_packet.get("next_executor_payload_hints", {}).get("require_validation_before_accept") and not next_validation_commands:
        next_constraints.append("Validation commands must be provided or clarified before the next run can be accepted.")

    escalation = None
    if repeated_same_verdict or int(sendback_packet.get("sendback_count") or 0) >= 3:
        escalation = {
            "level": "manager_review",
            "reason": "multiple sendbacks on the same coding line; consider narrower payload or manual decision",
        }

    return {
        "title": payload.get("title"),
        "goal": next_goal,
        "repo_path": payload.get("repo_path") or "",
        "task_type": payload.get("task_type") or "code",
        "constraints": next_constraints,
        "acceptance": next_acceptance,
        "files_of_interest": next_files,
        "validation_expectations": _dedupe_strings(list(payload.get("validation_expectations") or []) + retry_notes),
        "validation_commands": next_validation_commands,
        "allowed_actions": next_allowed_actions,
        "append_text": payload.get("append_text") or "",
        "replace_old": payload.get("replace_old") or "",
        "replace_new": payload.get("replace_new") or "",
        "sendback_context": {
            "requested_action": sendback_packet.get("requested_action"),
            "verdict": verdict,
            "reason": sendback_packet.get("reason"),
            "sendback_count": sendback_packet.get("sendback_count"),
            "blockers": blockers,
            "needs_input": needs_input,
            "risks": risks,
            "test_results": test_results,
            "files_changed": files_changed,
            "rollback_hint": sendback_packet.get("rollback_hint") or review_packet.get("rollback_hint") or "",
            "retry_strategy": sendback_packet.get("retry_strategy") or "",
        },
        "escalation_hint": escalation,
        "builder_meta": {
            "source": "outer_framework.sendback_payload_builder",
            "history_entries_considered": len(history),
            "repeated_same_verdict": repeated_same_verdict,
        },
    }


def build_rerun_gate(route_result: Dict[str, Any]) -> Dict[str, Any] | None:
    next_payload = route_result.get("next_executor_payload")
    sendback_packet = route_result.get("manager_sendback_packet") or {}
    if not next_payload or not sendback_packet:
        return None

    sendback_context = next_payload.get("sendback_context") or {}
    escalation_hint = next_payload.get("escalation_hint") or {}
    verdict = str(sendback_context.get("verdict") or sendback_packet.get("verdict") or "")
    sendback_count = int(sendback_context.get("sendback_count") or sendback_packet.get("sendback_count") or 0)
    blockers = _dedupe_strings(sendback_context.get("blockers") or [])
    needs_input = _dedupe_strings(sendback_context.get("needs_input") or [])
    validation_commands = [str(x).strip() for x in (next_payload.get("validation_commands") or []) if str(x).strip()]
    repeated_same_verdict = bool((next_payload.get("builder_meta") or {}).get("repeated_same_verdict"))

    if blockers or needs_input:
        return {
            "eligible": False,
            "decision": "hold",
            "reason": "missing input or blockers must be resolved before rerun",
            "required_actions": _dedupe_strings(blockers + needs_input),
            "rerun_mode": "none",
            "manager_review_required": True,
        }

    if not validation_commands:
        return {
            "eligible": False,
            "decision": "hold",
            "reason": "validation commands missing; rerun would not be review-safe",
            "required_actions": ["provide or clarify validation commands before rerun"],
            "rerun_mode": "none",
            "manager_review_required": True,
        }

    rerun_mode = "narrow_retry"
    if verdict == "blocked":
        rerun_mode = "blocked_retry_after_unblock"

    manager_review_required = False
    if escalation_hint or repeated_same_verdict or sendback_count >= 3:
        manager_review_required = True
        rerun_mode = "manager_review_before_retry"

    decision = "allow_rerun" if not manager_review_required else "review_then_rerun"
    reason = "rerun payload is sufficiently narrowed and validation-backed"
    if manager_review_required:
        reason = "repeated sendback pattern detected; manager review required before rerun"

    return {
        "eligible": True,
        "decision": decision,
        "reason": reason,
        "required_actions": [],
        "rerun_mode": rerun_mode,
        "manager_review_required": manager_review_required,
    }


def build_rerun_request(payload: Dict[str, Any], route_result: Dict[str, Any]) -> Dict[str, Any] | None:
    next_payload = route_result.get("next_executor_payload")
    rerun_gate = route_result.get("rerun_gate") or {}
    if not next_payload or not rerun_gate or not rerun_gate.get("eligible"):
        return None

    request_mode = "ready"
    if rerun_gate.get("decision") == "review_then_rerun":
        request_mode = "await_manager_review"

    return {
        "request_kind": "coding_executor_rerun",
        "request_mode": request_mode,
        "decision": rerun_gate.get("decision"),
        "rerun_mode": rerun_gate.get("rerun_mode"),
        "manager_review_required": bool(rerun_gate.get("manager_review_required")),
        "title": payload.get("title"),
        "repo_path": next_payload.get("repo_path") or payload.get("repo_path") or "",
        "executor_payload": next_payload,
        "source": {
            "framework": "outer_framework_skeleton",
            "sendback_count": route_result.get("sendback_count") or 0,
            "normalized_status": normalize_outer_status(route_result),
        },
    }



def classify_task_shape(payload: Dict[str, Any]) -> Dict[str, Any]:
    task_type = str(payload.get("task_type") or "general")
    acceptance = list(payload.get("acceptance") or [])
    priority = str(payload.get("priority") or "normal")
    requires_artifact = any("artifact" in str(item).lower() for item in acceptance)
    explicit_staged = bool(payload.get("force_multi_agent_lite"))

    return {
        "task_type": task_type,
        "priority": priority,
        "acceptance_count": len(acceptance),
        "requires_artifact": requires_artifact,
        "explicit_staged": explicit_staged,
        "is_direct_candidate": task_type in DIRECT_TASK_TYPES and priority not in {"high", "critical"},
        "is_light_candidate": task_type in LIGHT_TASK_TYPES and len(acceptance) <= 2,
    }


def explain_route(task_shape: Dict[str, Any], route: str) -> str:
    if route == "direct":
        return "task is simple enough for direct handling without staged collaboration"
    if route == "light_role_check":
        return "task benefits from lightweight structure but does not justify full staged orchestration"
    if task_shape.get("explicit_staged"):
        return "task explicitly requested staged collaboration"
    if task_shape.get("requires_artifact"):
        return "task requires artifact-oriented delivery and review-capable staged handling"
    return "task complexity or priority justifies multi_agent_lite staged collaboration"


def normalize_outer_status(route_result: Dict[str, Any]) -> str:
    final_status = str(route_result.get("final_status") or "DONE")
    packet = route_result.get("task_result_packet") or {}
    packet_status = str(packet.get("status") or "")
    coding_exec = route_result.get("coding_executor_result") or {}
    review_packet = coding_exec.get("review_packet") or {}
    review_verdict = str(review_packet.get("verdict") or "")
    coding_status = str(coding_exec.get("status") or "")
    coding_test_results = [str(x) for x in (coding_exec.get("test_results") or []) if str(x).strip()]

    if review_verdict == "blocked" or coding_status == "blocked":
        return "blocked"
    if review_verdict == "needs_replan":
        return "needs_replan"
    if any("blocked" in x.lower() for x in coding_test_results):
        return "blocked"
    if any("failed" in x.lower() for x in coding_test_results):
        return "needs_replan"
    if final_status == "READY":
        return "needs_execution_rerun"
    if final_status == "PLAN":
        return "needs_replan"
    if final_status == "BLOCKED":
        return "blocked"
    if final_status == "FAILED":
        return "failed"
    if packet_status == "blocked":
        return "blocked"
    if packet_status == "failed":
        return "failed"
    if final_status == "DONE" and packet_status == "success":
        return "completed"
    return "in_progress"


def build_writeback_policy(route_result: Dict[str, Any]) -> Dict[str, Any]:
    packet = route_result.get("task_result_packet") or {}
    final_status = str(route_result.get("final_status") or "DONE")
    packet_status = str(packet.get("status") or "")
    advisory = route_result.get("writeback_hint") or {"level": 0, "targets": []}
    normalized = normalize_outer_status(route_result)

    should_write_summary = normalized == "completed" and final_status == "DONE" and packet_status == "success"
    should_write_memory = should_write_summary and advisory.get("level", 0) >= 2
    should_write_state = normalized in {"needs_execution_rerun", "needs_replan", "blocked"}

    return {
        "advisory_only": True,
        "should_write_summary": should_write_summary,
        "should_write_memory": should_write_memory,
        "should_write_state": should_write_state,
        "recommended_targets": advisory.get("targets") or [],
        "reason": "outer framework retains final authority for memory/docs/state writes",
    }


def build_manager_sendback_packet(route_result: Dict[str, Any]) -> Dict[str, Any] | None:
    coding_exec = route_result.get("coding_executor_result") or {}
    review_packet = coding_exec.get("review_packet") or {}
    verdict = str(review_packet.get("verdict") or "")
    if verdict not in {"needs_replan", "blocked"}:
        return None

    files_changed = [str(x) for x in (coding_exec.get("files_changed") or []) if str(x).strip()]
    blockers = [str(x) for x in (coding_exec.get("blockers") or []) if str(x).strip()]
    needs_input = [str(x) for x in (coding_exec.get("needs_input") or []) if str(x).strip()]
    risks = [str(x) for x in (coding_exec.get("risks") or []) if str(x).strip()]
    tests_run = [str(x) for x in (coding_exec.get("tests_run") or []) if str(x).strip()]
    test_results = [str(x) for x in (coding_exec.get("test_results") or []) if str(x).strip()]
    previous_sendback_count = int(route_result.get("sendback_count") or 0)

    requested_action = "replan" if verdict == "needs_replan" else "unblock_or_clarify"
    retry_strategy = "manager should refine scope and rerun coding executor with narrower instructions"
    if verdict == "blocked":
        retry_strategy = "manager should resolve blockers or collect missing input before rerun"

    file_handling = "keep_changed_files_for_review"
    if verdict == "blocked" and files_changed:
        file_handling = "review_and_possibly_revert_changed_files_before_retry"
    if not files_changed:
        file_handling = "no_file_revert_needed"

    return {
        "requested_action": requested_action,
        "reason": review_packet.get("manager_action_suggestion") or verdict,
        "verdict": verdict,
        "confidence": review_packet.get("confidence") or "low",
        "sendback_count": previous_sendback_count + 1,
        "why": {
            "blockers": blockers,
            "needs_input": needs_input,
            "risks": risks,
            "tests_run": tests_run,
            "test_results": test_results,
        },
        "retry_strategy": retry_strategy,
        "files_changed": files_changed,
        "file_handling": file_handling,
        "rollback_hint": review_packet.get("rollback_hint") or "",
        "next_executor_payload_hints": {
            "tighten_target_files": True,
            "tighten_allowed_actions": verdict == "blocked",
            "require_validation_before_accept": True,
        },
    }


def _build_coding_executor_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": payload.get("title"),
        "goal": payload.get("goal"),
        "repo_path": payload.get("repo_path") or "",
        "task_type": payload.get("task_type") or "code",
        "constraints": payload.get("constraints") or [],
        "acceptance": payload.get("acceptance") or [],
        "files_of_interest": payload.get("files_of_interest") or [],
        "validation_expectations": payload.get("validation_expectations") or [],
        "validation_commands": payload.get("validation_commands") or [],
        "allowed_actions": payload.get("allowed_actions") or [],
        "append_text": payload.get("append_text") or "",
        "replace_old": payload.get("replace_old") or "",
        "replace_new": payload.get("replace_new") or "",
    }


def _run_direct(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = str(payload.get("goal") or payload.get("title") or "direct task")
    raw_task = _build_direct_raw_task(payload, summary)
    return {
        "route": "direct",
        "final_status": "DONE",
        "task_result_packet": raw_task["task_result_packet"],
        "writeback_hint": raw_task["writeback_hint"],
        "degrade_history": [],
        "sendback_count": 0,
        "artifact_lifecycle": [],
        "raw_task": raw_task,
    }


def _run_light_role_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = f"light role check completed for: {str(payload.get('title') or payload.get('goal') or 'task')}"
    raw_task = _build_light_raw_task(payload, summary)
    return {
        "route": "light_role_check",
        "final_status": "DONE",
        "task_result_packet": raw_task["task_result_packet"],
        "writeback_hint": raw_task["writeback_hint"],
        "degrade_history": [],
        "sendback_count": 0,
        "artifact_lifecycle": [],
        "raw_task": raw_task,
    }


def converge_outer_result(payload: Dict[str, Any], route_result: Dict[str, Any], task_shape: Dict[str, Any], run_trace: Dict[str, Any], writeback_plan: Dict[str, Any], writeback_stub: Dict[str, Any] | None = None) -> Dict[str, Any]:
    packet = route_result.get("task_result_packet") or {}
    route = str(route_result.get("route") or "direct")
    sendback_packet = route_result.get("manager_sendback_packet")
    next_payload = route_result.get("next_executor_payload")
    rerun_gate = route_result.get("rerun_gate")
    rerun_request = route_result.get("rerun_request")
    result = {
        "framework": "outer_framework_skeleton",
        "run_id": run_trace.get("run_id"),
        "title": payload.get("title"),
        "goal": payload.get("goal"),
        "task_shape": task_shape,
        "route": route,
        "route_explanation": explain_route(task_shape, route),
        "final_status": route_result.get("final_status", "DONE"),
        "normalized_status": normalize_outer_status(route_result),
        "summary": packet.get("summary", ""),
        "task_result_packet": packet,
        "writeback_hint": route_result.get("writeback_hint") or {"level": 0, "targets": []},
        "writeback_policy": build_writeback_policy(route_result),
        "writeback_plan": writeback_plan,
        "writeback_stub": writeback_stub,
        "manager_sendback_packet": sendback_packet,
        "next_executor_payload": next_payload,
        "rerun_gate": rerun_gate,
        "rerun_request": rerun_request,
        "sendback_history": route_result.get("sendback_history") or [],
        "sendback_history_path": route_result.get("sendback_history_path"),
        "degrade_history": route_result.get("degrade_history") or [],
        "sendback_count": int(route_result.get("sendback_count") or 0),
        "artifact_lifecycle": route_result.get("artifact_lifecycle") or [],
        "run_trace": run_trace,
        "raw_task": route_result.get("raw_task"),
    }
    if is_coding_task({
        "task_type": payload.get("task_type"),
        "title": payload.get("title"),
        "goal": payload.get("goal"),
    }):
        result["coding_result_packet"] = build_code_result_packet(route_result.get("raw_task") or payload, packet)
        if route_result.get("coding_executor_result"):
            result["coding_executor_result"] = route_result.get("coding_executor_result")
    return result


def run_outer_framework(root: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = f"OUTER-{uuid4().hex[:10].upper()}"
    started_at = _utc_now()
    task_shape = classify_task_shape(payload)
    route = choose_route(payload)
    route_explanation = explain_route(task_shape, route)

    if route == "direct":
        route_result = _run_direct(payload)
    elif route == "light_role_check":
        route_result = _run_light_role_check(payload)
    else:
        route_result = run_adapter(root, payload)

    finished_at = _utc_now()
    run_trace = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "route": route,
        "route_explanation": route_explanation,
        "title": payload.get("title"),
        "task_type": payload.get("task_type"),
        "task_id": (route_result.get("raw_task") or {}).get("task_id") if isinstance(route_result.get("raw_task"), dict) else route_result.get("task_id"),
    }
    if is_coding_task({
        "task_type": payload.get("task_type"),
        "title": payload.get("title"),
        "goal": payload.get("goal"),
    }) and str(payload.get("repo_path") or "").strip():
        task_key = _task_sendback_key(payload, route_result)
        history = _load_sendback_history(root, task_key)
        route_result["sendback_history"] = history
        route_result["sendback_count"] = len(history)

        coding_exec = materialize_coding_run(root, _build_coding_executor_payload(payload))
        run_trace["coding_executor_artifact"] = coding_exec.get("artifact")
        route_result["coding_executor_result"] = coding_exec.get("result")
        coding_result = coding_exec.get("result") or {}
        review_packet = coding_result.get("review_packet") or {}
        review_verdict = str(review_packet.get("verdict") or "")
        coding_status = str(coding_result.get("status") or "")
        coding_test_results = [str(x) for x in (coding_result.get("test_results") or []) if str(x).strip()]
        if review_verdict == "blocked" or coding_status == "blocked" or any("blocked" in x.lower() for x in coding_test_results):
            route_result["final_status"] = "BLOCKED"
        elif review_verdict == "needs_replan" or any("failed" in x.lower() for x in coding_test_results):
            route_result["final_status"] = "PLAN"

        sendback_packet = build_manager_sendback_packet(route_result)
        route_result["manager_sendback_packet"] = sendback_packet
        if sendback_packet:
            history_entry = {
                "run_id": run_id,
                "requested_action": sendback_packet.get("requested_action"),
                "verdict": sendback_packet.get("verdict"),
                "reason": sendback_packet.get("reason"),
                "timestamp": finished_at,
            }
            history = history + [history_entry]
            route_result["sendback_history"] = history
            route_result["sendback_count"] = len(history)
            route_result["sendback_history_path"] = _store_sendback_history(root, task_key, history)
            route_result["next_executor_payload"] = build_next_executor_payload(payload, route_result)
            route_result["rerun_gate"] = build_rerun_gate(route_result)
            route_result["rerun_request"] = build_rerun_request(payload, route_result)
        else:
            route_result["sendback_history_path"] = _sendback_runtime_dir(root).joinpath(f"{task_key}.json").as_posix() if history else None
            route_result["next_executor_payload"] = None
            route_result["rerun_gate"] = None
            route_result["rerun_request"] = None

    run_trace["final_status"] = route_result.get("final_status", "DONE")
    run_trace["normalized_status"] = normalize_outer_status(route_result)

    _append_registry_row(root, run_trace)
    writeback_plan = build_writeback_plan({
        "run_id": run_id,
        "normalized_status": normalize_outer_status(route_result),
        "task_result_packet": route_result.get("task_result_packet") or {},
        "writeback_hint": route_result.get("writeback_hint") or {"level": 0, "targets": []},
        "writeback_policy": build_writeback_policy(route_result),
    })
    writeback_stub = materialize_writeback_stub(root, writeback_plan)

    return converge_outer_result(payload, route_result, task_shape, run_trace, writeback_plan, writeback_stub)
