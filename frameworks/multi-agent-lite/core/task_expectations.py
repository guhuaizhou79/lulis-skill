from __future__ import annotations

from typing import Any, Dict


TASK_TYPE_EXPECTATIONS: Dict[str, Dict[str, Any]] = {
    "code": {
        "expected_execution_role": "execution_code",
        "requires_meaningful_changes": True,
        "artifacts_preferred": True,
        "strict_review": False,
    },
    "framework_design": {
        "expected_execution_role": "execution_code",
        "requires_meaningful_changes": True,
        "artifacts_preferred": False,
        "strict_review": True,
    },
    "automation": {
        "expected_execution_role": "execution_code",
        "requires_meaningful_changes": True,
        "artifacts_preferred": True,
        "strict_review": True,
    },
    "general": {
        "expected_execution_role": "execution_general",
        "requires_meaningful_changes": False,
        "artifacts_preferred": False,
        "strict_review": False,
    },
}


def get_task_expectations(task_type: str) -> Dict[str, Any]:
    return TASK_TYPE_EXPECTATIONS.get(task_type, TASK_TYPE_EXPECTATIONS["general"])
