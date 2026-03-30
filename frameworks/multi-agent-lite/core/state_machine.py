from __future__ import annotations

from typing import Dict, List

TRANSITIONS: Dict[str, List[str]] = {
    "NEW": ["PLAN", "CANCELLED"],
    "PLAN": ["READY", "BLOCKED", "FAILED", "CANCELLED"],
    "READY": ["EXECUTING", "BLOCKED", "CANCELLED"],
    "EXECUTING": ["REVIEW", "PLAN", "BLOCKED", "FAILED", "CANCELLED"],
    "REVIEW": ["DONE", "PLAN", "EXECUTING", "FAILED", "CANCELLED"],
    "DONE": [],
    "BLOCKED": ["PLAN", "EXECUTING", "CANCELLED"],
    "FAILED": ["PLAN", "CANCELLED"],
    "CANCELLED": [],
}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, [])


def assert_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise ValueError(f"illegal transition: {current} -> {target}")
