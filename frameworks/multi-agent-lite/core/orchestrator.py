from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4
from datetime import datetime, timezone
import json

from .delivery_synthesizer import synthesize_delivery
from .dispatcher import Dispatcher
from .execution_runner import execute_subtasks
from .mock_executor import MockExecutor
from .openclaw_executor import OpenClawExecutor
from .planner import build_plan, select_planning_profile
from .reporting import summarize_dispatches
from .review_engine import ReviewEngine
from .review_state import apply_review
from .router import ModelRouter
from .state_machine import assert_transition
from .task_store import TaskStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Orchestrator:
    root: Path

    def __post_init__(self) -> None:
        self.store = TaskStore(self.root / "runtime" / "tasks")
        self.router = ModelRouter(self.root / "configs" / "models.json")
        self.dispatcher = Dispatcher(self.router)
        self.reviewer = ReviewEngine()
        self.executor = self._build_executor()

    def _runtime_dir(self) -> Path:
        path = self.root / "runtime" / "orchestrator"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _trace_dir(self) -> Path:
        path = self._runtime_dir() / "traces"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _event_registry_path(self) -> Path:
        return self._runtime_dir() / "registry.jsonl"

    def _snapshot_for_trace(self, task: Dict[str, Any]) -> Dict[str, Any]:
        last_review = task.get("last_review") or {}
        return {
            "task_id": task.get("task_id"),
            "title": task.get("title"),
            "goal": task.get("goal"),
            "task_type": task.get("task_type"),
            "priority": task.get("priority"),
            "status": task.get("status"),
            "owner": task.get("owner"),
            "planning_profile": task.get("planning_profile"),
            "orchestration_mode": task.get("orchestration_mode"),
            "sendback_count": task.get("sendback_count", 0),
            "rerun_execution_only": bool(task.get("rerun_execution_only")),
            "dispatch_summary": task.get("dispatch_summary") or {},
            "delivery_status": task.get("delivery_status"),
            "delivery_summary": task.get("delivery_summary") or "",
            "deliverables": list(task.get("deliverables") or []),
            "artifacts": list(task.get("artifacts") or []),
            "degrade_history": list(task.get("degrade_history") or []),
            "writeback_hint": task.get("writeback_hint") or {"level": 0, "targets": []},
            "last_review": {
                "review_id": last_review.get("review_id"),
                "decision": last_review.get("decision"),
                "next_action": last_review.get("next_action"),
                "recommended_sendback_target": last_review.get("recommended_sendback_target"),
                "delivery_status": last_review.get("delivery_status"),
                "blocking_gaps": list(last_review.get("blocking_gaps") or []),
                "quality_signals": list(last_review.get("quality_signals") or []),
                "residual_risks": list(last_review.get("residual_risks") or []),
            },
            "task_result_packet": task.get("task_result_packet"),
            "subtasks": [
                {
                    "subtask_id": st.get("subtask_id"),
                    "role": st.get("assigned_role"),
                    "model": st.get("assigned_model"),
                    "dispatch_status": st.get("dispatch_status"),
                    "rerun_needed": bool(st.get("rerun_needed")),
                    "rerun_reason": list(st.get("rerun_reason") or []),
                    "objective": st.get("objective"),
                    "result_summary": (st.get("result") or {}).get("summary"),
                    "result_needs_input": list((st.get("result") or {}).get("needs_input") or []),
                    "result_risks": list((st.get("result") or {}).get("risks") or []),
                }
                for st in (task.get("subtasks") or [])
            ],
            "history_tail": list((task.get("history") or [])[-10:]),
        }

    def _append_trace_event(self, task: Dict[str, Any], event: str, note: str = "") -> Dict[str, Any]:
        snapshot = self._snapshot_for_trace(task)
        row = {
            "ts": _utc_now(),
            "event": event,
            "task_id": task.get("task_id"),
            "status": task.get("status"),
            "task_type": task.get("task_type"),
            "priority": task.get("priority"),
            "orchestration_mode": task.get("orchestration_mode"),
            "delivery_status": task.get("delivery_status"),
            "sendback_count": task.get("sendback_count", 0),
            "note": note,
            "snapshot": snapshot,
        }
        trace_path = self._trace_dir() / f"{task['task_id']}.jsonl"
        with trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        with self._event_registry_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": row["ts"],
                "event": event,
                "task_id": task.get("task_id"),
                "status": task.get("status"),
                "task_type": task.get("task_type"),
                "priority": task.get("priority"),
                "orchestration_mode": task.get("orchestration_mode"),
                "delivery_status": task.get("delivery_status"),
                "sendback_count": task.get("sendback_count", 0),
                "note": note,
                "trace_path": str(trace_path),
            }, ensure_ascii=False) + "\n")
        task["orchestrator_trace_path"] = str(trace_path)
        task["orchestrator_last_event"] = event
        return task

    def _build_executor(self):
        mock = MockExecutor(self.root)
        cfg_path = self.root / "configs" / "executor.json"
        if not cfg_path.exists():
            return mock

        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return mock

        mode = cfg.get("mode", "mock")
        if mode == "openclaw":
            oc = cfg.get("openclaw", {})
            try:
                return OpenClawExecutor(
                    agent_id=oc.get("agent_id", "main"),
                    timeout=int(oc.get("timeout", 180)),
                )
            except FileNotFoundError:
                return mock
        return mock

    def _select_orchestration_mode(self, task_type: str, priority: str, acceptance: list[str]) -> str:
        if priority in {"high", "critical"} or task_type in {"automation", "framework_design"}:
            return "full"
        if acceptance:
            return "compact"
        return "minimal"

    def _apply_degrade(self, task: Dict[str, Any], reason: str) -> Dict[str, Any]:
        current = str(task.get("orchestration_mode") or "full")
        next_mode = {
            "full": "compact",
            "compact": "minimal",
            "minimal": "minimal",
        }.get(current, "compact")
        task["orchestration_mode"] = next_mode
        task.setdefault("degrade_history", []).append({
            "from": current,
            "to": next_mode,
            "reason": reason,
        })
        return task

    def _build_review_augmented_result(self, task: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
        packet = dict(task.get("task_result_packet") or {})
        packet["review_verdict"] = review.get("decision")
        packet["review_reasons"] = review.get("reasons", [])
        packet["delivery_status"] = review.get("delivery_status", task.get("delivery_status", "unknown"))
        packet["recommended_sendback_target"] = review.get("recommended_sendback_target", "none")
        packet["next_action"] = review.get("next_action")
        return packet

    def _mark_execution_rerun(self, task: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
        reasons = review.get("blocking_gaps", []) or []
        affected = set(review.get("affected_subtasks") or [])
        rerun_round = int(task.get("sendback_count", 0)) + 1
        marked = []
        for subtask in task.get("subtasks", []):
            role = str(subtask.get("assigned_role") or "")
            subtask_id = str(subtask.get("subtask_id") or "")
            should_rerun = role.startswith("execution_") and (
                not affected or subtask_id in affected or subtask.get("dispatch_status") != "completed"
            )
            if should_rerun:
                stale_result = dict(subtask.get("result") or {})
                if stale_result:
                    stale_result["stale"] = True
                    stale_result["stale_reason"] = reasons[:3]
                    stale_result["stale_round"] = rerun_round
                updated = {
                    **subtask,
                    "rerun_needed": True,
                    "rerun_reason": reasons[:3],
                    "dispatch_status": "ready",
                    "stale_result": stale_result or None,
                    "superseded_by_rerun_round": rerun_round,
                }
                marked.append(updated)
            else:
                marked.append({
                    **subtask,
                    "rerun_needed": False,
                })
        task["subtasks"] = marked
        task["rerun_execution_only"] = True
        return task

    def create_task(
        self,
        title: str,
        goal: str,
        task_type: str,
        priority: str = "normal",
        constraints: list[str] | None = None,
        acceptance: list[str] | None = None,
    ) -> Dict[str, Any]:
        acceptance = acceptance or []
        task = {
            "task_id": f"TASK-{uuid4().hex[:8].upper()}",
            "title": title,
            "goal": goal,
            "status": "NEW",
            "owner": "manager",
            "task_type": task_type,
            "priority": priority,
            "constraints": constraints or [],
            "acceptance": acceptance,
            "context_refs": [],
            "subtasks": [],
            "dispatch_summary": {},
            "artifacts": [],
            "deliverables": [],
            "delivery_summary": "",
            "delivery_status": "not_started",
            "orchestration_mode": self._select_orchestration_mode(task_type, priority, acceptance),
            "execution_budget": {
                "max_context_items": 8,
                "max_evidence_refs": 5,
                "max_sendback_rounds": 2,
            },
            "sendback_count": 0,
            "degrade_history": [],
            "writeback_hint": {"level": 0, "targets": []},
            "task_result_packet": None,
            "history": [],
            "reviews": [],
        }
        self.store.append_history(task, {"event": "task_created", "owner": "manager"})
        task = self._append_trace_event(task, "task_created", note="task created")
        self.store.save(task)
        return task

    def transition(self, task_id: str, target: str, note: str = "") -> Dict[str, Any]:
        task = self.store.load(task_id)
        assert_transition(task["status"], target)
        prev = task["status"]
        task["status"] = target
        self.store.append_history(task, {
            "event": "state_changed",
            "from": prev,
            "to": target,
            "note": note,
        })
        task = self._append_trace_event(task, "state_changed", note=f"{prev} -> {target}: {note}".strip())
        self.store.save(task)
        return task

    def role_model(self, role_key: str) -> Dict[str, Any]:
        return self.router.pick(role_key)

    def plan_task(self, task_id: str) -> Dict[str, Any]:
        task = self.store.load(task_id)
        if task["status"] == "NEW":
            task = self.transition(task_id, "PLAN", note="planning started")
        task["planning_profile"] = select_planning_profile(task)
        task["subtasks"] = build_plan(task)
        self.store.append_history(task, {
            "event": "plan_built",
            "subtask_count": len(task["subtasks"]),
        })
        task = self._append_trace_event(task, "plan_built", note=f"subtask_count={len(task['subtasks'])}")
        self.store.save(task)
        return task

    def dispatch_task(self, task_id: str) -> Dict[str, Any]:
        task = self.store.load(task_id)
        if not task.get("subtasks"):
            raise ValueError("cannot dispatch without subtasks")
        dispatched = [self.dispatcher.assign(st, task) for st in task["subtasks"]]
        task["subtasks"] = dispatched
        task["dispatch_summary"] = summarize_dispatches(dispatched)
        if task["status"] in {"PLAN", "NEW"}:
            assert_transition(task["status"], "READY")
            prev = task["status"]
            task["status"] = "READY"
            self.store.append_history(task, {
                "event": "state_changed",
                "from": prev,
                "to": "READY",
                "note": "subtasks dispatched and ready",
            })
        self.store.append_history(task, {
            "event": "task_dispatched",
            "summary": task["dispatch_summary"],
        })
        task = self._append_trace_event(task, "task_dispatched", note="subtasks dispatched")
        self.store.save(task)
        return task

    def execute_task(self, task_id: str) -> Dict[str, Any]:
        task = self.store.load(task_id)
        if task["status"] == "READY":
            assert_transition(task["status"], "EXECUTING")
            prev = task["status"]
            task["status"] = "EXECUTING"
            self.store.append_history(task, {
                "event": "state_changed",
                "from": prev,
                "to": "EXECUTING",
                "note": "executor started",
            })
        task = execute_subtasks(task, self.executor)
        task = synthesize_delivery(task)

        self.store.append_history(task, {
            "event": "execution_completed",
            "completed_subtasks": len(task.get("subtasks", [])),
        })
        task = self._append_trace_event(task, "execution_completed", note="execution pass completed")
        self.store.save(task)
        return task

    def review_task(self, task_id: str) -> Dict[str, Any]:
        task = self.store.load(task_id)
        if task["status"] == "EXECUTING":
            assert_transition(task["status"], "REVIEW")
            task["status"] = "REVIEW"
            self.store.append_history(task, {
                "event": "state_changed",
                "from": "EXECUTING",
                "to": "REVIEW",
                "note": "entered review loop",
            })
        review = self.reviewer.evaluate(task)
        task = apply_review(task, review)
        task["delivery_status"] = review.get("delivery_status", task.get("delivery_status", "unknown"))
        self.store.append_history(task, {
            "event": "review_completed",
            "decision": review["decision"],
            "next_action": review["next_action"],
            "delivery_status": task["delivery_status"],
        })
        task["task_result_packet"] = self._build_review_augmented_result(task, review)
        task = self._append_trace_event(task, "review_completed", note=f"decision={review['decision']} next_action={review['next_action']}")
        self.store.save(task)
        return task
