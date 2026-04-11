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
    return {
        "framework": "outer_framework_skeleton",
        "title": payload.get("title"),
        "goal": payload.get("goal"),
        "task_shape": task_shape,
        "route": route_result.get("route"),
        "final_status": route_result.get("final_status", "DONE"),
        "summary": packet.get("summary", ""),
        "task_result_packet": packet,
        "writeback_hint": route_result.get("writeback_hint") or {"level": 0, "targets": []},
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
