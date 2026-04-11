from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys
import tempfile


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from outer_framework import run_outer_framework


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _print(label: str, payload) -> None:
    print(f"\n== {label} ==")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)


def main() -> None:
    source_root = Path(__file__).resolve().parent
    temp_dir = Path(tempfile.mkdtemp(prefix="multi-agent-lite-outer-framework-verify-"))
    test_root = temp_dir / "multi-agent-lite"
    shutil.copytree(source_root, test_root)

    try:
        direct_payload = {
            "title": "simple answer",
            "goal": "answer a direct question",
            "task_type": "choice_answering",
            "priority": "normal",
            "acceptance": ["give the option directly"],
        }
        direct_result = run_outer_framework(test_root, direct_payload)
        _assert(direct_result.get("route") == "direct", "direct task should stay on direct route")
        _assert(direct_result.get("final_status") == "DONE", "direct route should finish as DONE")

        light_payload = {
            "title": "small structured pass",
            "goal": "perform a lightweight structured check",
            "task_type": "general",
            "priority": "normal",
            "acceptance": ["brief structured answer"],
        }
        light_result = run_outer_framework(test_root, light_payload)
        _assert(light_result.get("route") == "light_role_check", "general lightweight task should go to light_role_check")
        _assert(light_result.get("final_status") == "DONE", "light route should finish as DONE")

        staged_payload = {
            "title": "staged automation",
            "goal": "produce a delivery-ready artifact with review and compact result",
            "task_type": "automation",
            "priority": "high",
            "acceptance": [
                "materialize artifact",
                "include compact result packet",
                "allow review-driven recovery",
            ],
        }
        staged_result = run_outer_framework(test_root, staged_payload)
        _assert(staged_result.get("route") == "multi_agent_lite", "automation task should route into staged kernel")
        _assert(staged_result.get("task_result_packet"), "staged route should expose task_result_packet")
        _assert(staged_result.get("framework") == "outer_framework_skeleton", "outer framework marker should be present")

        _print("outer framework status", {
            "direct": {
                "route": direct_result.get("route"),
                "final_status": direct_result.get("final_status"),
                "summary": direct_result.get("summary"),
            },
            "light": {
                "route": light_result.get("route"),
                "final_status": light_result.get("final_status"),
                "summary": light_result.get("summary"),
            },
            "staged": {
                "route": staged_result.get("route"),
                "final_status": staged_result.get("final_status"),
                "summary": staged_result.get("summary"),
                "task_shape": staged_result.get("task_shape"),
            },
        })
        print("\nALL_CHECKS_PASSED")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
