from __future__ import annotations

from typing import Dict, Any


def apply_review(task: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
    task["last_review"] = review
    task.setdefault("reviews", []).append(review)
    return task
