from __future__ import annotations

from typing import Any, Dict


TASK_TYPE_EXPECTATIONS: Dict[str, Dict[str, Any]] = {
    "code": {
        "expected_execution_role": "execution_code",
        "requires_meaningful_changes": True,
        "artifacts_preferred": True,
        "strict_review": False,
        "output_shape": "code_or_config",
    },
    "framework_design": {
        "expected_execution_role": "execution_code",
        "requires_meaningful_changes": True,
        "artifacts_preferred": False,
        "strict_review": True,
        "output_shape": "structured_deliverable",
    },
    "automation": {
        "expected_execution_role": "execution_code",
        "requires_meaningful_changes": True,
        "artifacts_preferred": True,
        "strict_review": True,
        "output_shape": "code_or_config",
    },
    "fact_lookup": {
        "expected_execution_role": "execution_general",
        "requires_meaningful_changes": False,
        "artifacts_preferred": False,
        "strict_review": False,
        "output_shape": "direct_answer",
    },
    "choice_answering": {
        "expected_execution_role": "execution_general",
        "requires_meaningful_changes": False,
        "artifacts_preferred": False,
        "strict_review": True,
        "output_shape": "choice_then_reason",
    },
    "config_authoring": {
        "expected_execution_role": "execution_code",
        "requires_meaningful_changes": True,
        "artifacts_preferred": True,
        "strict_review": True,
        "output_shape": "config_first",
    },
    "path_lookup": {
        "expected_execution_role": "execution_general",
        "requires_meaningful_changes": False,
        "artifacts_preferred": False,
        "strict_review": True,
        "output_shape": "path_or_identifier",
    },
    "general": {
        "expected_execution_role": "execution_general",
        "requires_meaningful_changes": False,
        "artifacts_preferred": False,
        "strict_review": False,
        "output_shape": "general_deliverable",
    },
}


def get_task_expectations(task_type: str) -> Dict[str, Any]:
    return TASK_TYPE_EXPECTATIONS.get(task_type, TASK_TYPE_EXPECTATIONS["general"])
