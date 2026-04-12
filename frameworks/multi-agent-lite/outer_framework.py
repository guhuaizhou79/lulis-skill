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
        else:
            route_result["sendback_history_path"] = _sendback_runtime_dir(root).joinpath(f"{task_key}.json").as_posix() if history else None

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
