from __future__ import annotations

from typing import Any, Dict

from .router import ModelRouter


class Dispatcher:
    def __init__(self, router: ModelRouter):
        self.router = router

    def assign(self, subtask: Dict[str, Any]) -> Dict[str, Any]:
        role_key = subtask["assigned_role"]
        model_cfg = self.router.pick(role_key)
        return {
            **subtask,
            "assigned_model": model_cfg["primary"],
            "fallback_models": model_cfg.get("fallback", []),
            "dispatch_status": "ready",
        }
