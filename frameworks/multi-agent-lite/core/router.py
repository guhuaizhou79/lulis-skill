from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class ModelRouter:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = json.loads(self.config_path.read_text(encoding="utf-8"))

    def pick(self, role_key: str) -> Dict[str, Any]:
        if role_key not in self.config:
            raise KeyError(f"unknown role key: {role_key}")
        return self.config[role_key]
