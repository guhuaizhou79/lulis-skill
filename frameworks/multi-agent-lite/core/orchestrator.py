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
        cfg_path = self.root / "configs" / "executor.json"
        if not cfg_path.exists():
            return MockExecutor()

        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return MockExecutor()

        mode = cfg.get("mode", "mock")
        if mode == "openclaw":
            oc = cfg.get("openclaw", {})
            try:
                return OpenClawExecutor(
                    agent_id=oc.get("agent_id", "main"),
                    timeout=int(oc.get("timeout", 180)),
                )
            except FileNotFoundError:
                return MockExecutor()
        return MockExecutor()

    def create_task(
        self,
        title: str,
        goal: str,
        task_type: str,
        priority: str = "normal",
        constraints: list[str] | None = None,
        acceptance: list[str] | None = None,
    ) -> Dict[str, Any]:
        task = {
            "task_id": f"TASK-{uuid4().hex[:8].upper()}",
            "title": title,
            "goal": goal,
            "status": "NEW",
            "owner": "manager",
            "task_type": task_type,
            "priority": priority,
            "constraints": constraints or [],
            "acceptance": acceptance or [],
            "context_refs": [],
            "subtasks": [],
            "dispatch_summary": {},
            "artifacts": [],
            "deliverables": [],
            "delivery_summary": "",
            "delivery_status": "not_started",
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
        dispatched = [self.dispatcher.assign(st) for st in task["subtasks"]]
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
        target = "DONE" if review["decision"] == "approved" else "PLAN"
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
