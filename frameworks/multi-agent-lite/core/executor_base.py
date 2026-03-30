from __future__ import annotations

from typing import Any, Dict, Protocol


class Executor(Protocol):
    def run(self, role: str, subtask: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        ...
