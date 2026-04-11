from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import sys


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from outer_adapter import choose_route, run_adapter


DIRECT_TASK_TYPES = {"choice_answering", "path_lookup", "fact_lookup"}
LIGHT_TASK_TYPES = {"general", "config_authoring"}


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

    if final_status == "DONE" and packet_status == "success":
        return "completed"
    if final_status == "READY":
        return "needs_execution_rerun"
    if final_status == "PLAN":
        return "needs_replan"
    if final_status == "BLOCKED" or packet_status == "blocked":
        return "blocked"
    if final_status == "FAILED" or packet_status == "failed":
        return "failed"
    return "in_progress"


def build_writeback_policy(route_result: Dict[str, Any]) -> Dict[str, Any]:
    packet = route_result.get("task_result_packet") or {}
    final_status = str(route_result.get("final_status") or "DONE")
    packet_status = str(packet.get("status") or "")
    advisory = route_result.get("writeback_hint") or {"level": 0, "targets": []}

    should_write_summary = final_status == "DONE" and packet_status == "success"
    should_write_memory = should_write_summary and advisory.get("level", 0) >= 2
    should_write_state = final_status in {"READY", "PLAN", "BLOCKED"}

    return {
        "advisory_only": True,
        "should_write_summary": should_write_summary,
        "should_write_memory": should_write_memory,
        "should_write_state": should_write_state,
        "recommended_targets": advisory.get("targets") or [],
        "reason": "outer framework retains final authority for memory/docs/state writes",
    }


def _run_direct(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = str(payload.get("goal") or payload.get("title") or "direct task")
    return {
        "route": "direct",
        "final_status": "DONE",
        "task_result_packet": {
            "status": "success",
            "summary": summary,
            "deliverables": [],
            "changes": [],
            "risks": [],
            "needs_input": [],
            "evidence_refs": [],
            "writeback_recommendation": {"level": 0, "targets": []},
        },
        "writeback_hint": {"level": 0, "targets": []},
        "degrade_history": [],
        "sendback_count": 0,
        "artifact_lifecycle": [],
        "raw_task": None,
    }


def _run_light_role_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = f"light role check completed for: {str(payload.get('title') or payload.get('goal') or 'task')}"
    return {
        "route": "light_role_check",
        "final_status": "DONE",
        "task_result_packet": {
            "status": "success",
            "summary": summary,
            "deliverables": [],
            "changes": ["performed lightweight structured pass"],
            "risks": [],
            "needs_input": [],
            "evidence_refs": [],
            "writeback_recommendation": {"level": 0, "targets": []},
        },
        "writeback_hint": {"level": 0, "targets": []},
        "degrade_history": [],
        "sendback_count": 0,
        "artifact_lifecycle": [],
        "raw_task": None,
    }


def converge_outer_result(payload: Dict[str, Any], route_result: Dict[str, Any], task_shape: Dict[str, Any]) -> Dict[str, Any]:
    packet = route_result.get("task_result_packet") or {}
    route = str(route_result.get("route") or "direct")
    return {
        "framework": "outer_framework_skeleton",
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
        "degrade_history": route_result.get("degrade_history") or [],
        "sendback_count": int(route_result.get("sendback_count") or 0),
        "artifact_lifecycle": route_result.get("artifact_lifecycle") or [],
        "raw_task": route_result.get("raw_task"),
    }


def run_outer_framework(root: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    task_shape = classify_task_shape(payload)
    route = choose_route(payload)

    if route == "direct":
        route_result = _run_direct(payload)
    elif route == "light_role_check":
        route_result = _run_light_role_check(payload)
    else:
        route_result = run_adapter(root, payload)

    return converge_outer_result(payload, route_result, task_shape)
