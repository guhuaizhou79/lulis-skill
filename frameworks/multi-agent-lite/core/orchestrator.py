from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4
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


@dataclass
class Orchestrator:
    root: Path

    def __post_init__(self) -> None:
        self.store = TaskStore(self.root / "runtime" / "tasks")
        self.router = ModelRouter(self.root / "configs" / "models.json")
        self.dispatcher = Dispatcher(self.router)
        self.reviewer = ReviewEngine()
        self.executor = self._build_executor()

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
        })
        prev = task["status"]
        if review["decision"] == "approved":
            target = "DONE"
        else:
            task["sendback_count"] = int(task.get("sendback_count", 0)) + 1
            max_rounds = int((task.get("execution_budget") or {}).get("max_sendback_rounds", 2))
            if task["sendback_count"] >= max_rounds:
                task = self._apply_degrade(task, reason="sendback threshold reached")
            next_action = review.get("next_action", "PLAN")
            if next_action == "BLOCKED":
                target = "BLOCKED"
            elif next_action == "EXECUTING":
                task = self._mark_execution_rerun(task, review)
                target = "READY"
            else:
                target = "PLAN"
        task["task_result_packet"] = self._build_review_augmented_result(task, review)
        assert_transition(prev, target)
        task["status"] = target
        self.store.append_history(task, {
            "event": "state_changed",
            "from": prev,
            "to": target,
            "note": "review outcome applied",
        })
        self.store.save(task)
        return task
