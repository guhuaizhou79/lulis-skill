from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import sys


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from .core.orchestrator import Orchestrator
except ImportError:
    from core.orchestrator import Orchestrator


DIRECT_TASK_TYPES = {"choice_answering", "path_lookup", "fact_lookup"}
LIGHT_TASK_TYPES = {"general", "config_authoring"}
STAGED_TASK_TYPES = {"automation", "framework_design", "code"}


def choose_route(payload: Dict[str, Any]) -> str:
    task_type = str(payload.get("task_type") or "general")
    acceptance = payload.get("acceptance") or []
    priority = str(payload.get("priority") or "normal")
    wants_staged = bool(payload.get("force_multi_agent_lite"))

    if wants_staged:
        return "multi_agent_lite"
    if task_type in DIRECT_TASK_TYPES and priority not in {"high", "critical"}:
        return "direct"
    if task_type in LIGHT_TASK_TYPES and len(acceptance) <= 2:
        return "light_role_check"
    if task_type in STAGED_TASK_TYPES or priority in {"high", "critical"} or len(acceptance) >= 3:
        return "multi_agent_lite"
    return "light_role_check"


def build_outer_result(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "route": "multi_agent_lite",
        "task_id": task.get("task_id"),
        "final_status": task.get("status"),
        "orchestration_mode": task.get("orchestration_mode"),
        "task_result_packet": task.get("task_result_packet"),
        "writeback_hint": task.get("writeback_hint") or {"level": 0, "targets": []},
        "degrade_history": task.get("degrade_history") or [],
        "sendback_count": int(task.get("sendback_count") or 0),
        "artifact_lifecycle": task.get("artifact_lifecycle") or [],
        "raw_task": task,
    }


def run_multi_agent_lite(root: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    orch = Orchestrator(root)
    task = orch.create_task(
        title=str(payload.get("title") or "untitled task"),
        goal=str(payload.get("goal") or ""),
        task_type=str(payload.get("task_type") or "general"),
        priority=str(payload.get("priority") or "normal"),
        constraints=list(payload.get("constraints") or []),
        acceptance=list(payload.get("acceptance") or []),
    )
    task_id = str(task["task_id"])

    task = orch.plan_task(task_id)
    task = orch.dispatch_task(task_id)
    task = orch.execute_task(task_id)
    task = orch.review_task(task_id)
    return build_outer_result(task)


def run_adapter(root: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    route = choose_route(payload)
    if route != "multi_agent_lite":
        return {
            "route": route,
            "reason": "payload does not currently require staged collaboration",
            "task_result_packet": None,
        }
    return run_multi_agent_lite(root, payload)
