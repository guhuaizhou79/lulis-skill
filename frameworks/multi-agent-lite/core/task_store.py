from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class TaskStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def task_path(self, task_id: str) -> Path:
        return self.base_dir / f"{task_id}.json"

    def load(self, task_id: str) -> Dict[str, Any]:
        return json.loads(self.task_path(task_id).read_text(encoding="utf-8"))

    def save(self, task: Dict[str, Any]) -> Path:
        path = self.task_path(task["task_id"])
        path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def append_history(self, task: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
        task.setdefault("history", []).append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            **event,
        })
        return task
