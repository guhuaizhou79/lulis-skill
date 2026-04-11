from __future__ import annotations

from typing import Any, Dict

from .router import ModelRouter


class Dispatcher:
    def __init__(self, router: ModelRouter):
        self.router = router

    def _budget(self, task: Dict[str, Any]) -> Dict[str, int]:
        budget = task.get("execution_budget") or {}
        return {
            "max_context_items": int(budget.get("max_context_items", 8)),
            "max_evidence_refs": int(budget.get("max_evidence_refs", 5)),
        }

    def _trim_list(self, items: list[Any], limit: int) -> list[str]:
        out: list[str] = []
        seen = set()
        for item in items or []:
            value = str(item or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)
            if len(out) >= limit:
                break
        return out

    def build_handoff(self, subtask: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        budget = self._budget(task)
        return {
            "goal": str(subtask.get("objective") or task.get("goal") or "").strip(),
            "input_scope": self._trim_list(task.get("context_refs", []), budget["max_context_items"]),
            "constraints": self._trim_list(task.get("constraints", []), budget["max_context_items"]),
            "acceptance_focus": self._trim_list(task.get("acceptance", []), budget["max_context_items"]),
            "evidence_refs": self._trim_list(task.get("artifacts", []), budget["max_evidence_refs"]),
            "output_contract": "result.schema.json",
            "budget": budget,
        }

    def assign(self, subtask: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        role_key = subtask["assigned_role"]
        model_cfg = self.router.pick(role_key)
        return {
            **subtask,
            "assigned_model": model_cfg["primary"],
            "fallback_models": model_cfg.get("fallback", []),
            "dispatch_status": "ready",
            "handoff": self.build_handoff(subtask, task),
        }
