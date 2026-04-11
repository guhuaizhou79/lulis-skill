from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys
import tempfile


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from outer_adapter import choose_route, run_adapter


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
    temp_dir = Path(tempfile.mkdtemp(prefix="multi-agent-lite-adapter-verify-"))
    test_root = temp_dir / "multi-agent-lite"
    shutil.copytree(source_root, test_root)

    try:
        direct_payload = {
            "title": "simple choice",
            "goal": "pick one option",
            "task_type": "choice_answering",
            "priority": "normal",
            "acceptance": ["option first"],
        }
        route = choose_route(direct_payload)
        _assert(route == "direct", "choice_answering should route to direct by default")

        staged_payload = {
            "title": "staged automation task",
            "goal": "produce a delivery-ready artifact with review",
            "task_type": "automation",
            "priority": "high",
            "acceptance": [
                "materialize artifact",
                "include compact result packet",
                "support review decision",
            ],
        }
        result = run_adapter(test_root, staged_payload)
        _assert(result.get("route") == "multi_agent_lite", "high-priority automation should route to multi_agent_lite")
        _assert(result.get("task_result_packet"), "adapter result should include task_result_packet")
        _assert(result.get("final_status") in {"DONE", "READY", "PLAN", "BLOCKED"}, "adapter final_status should be normalized")

        _print("outer adapter status", {
            "direct_route": route,
            "staged_result": {
                "route": result.get("route"),
                "task_id": result.get("task_id"),
                "final_status": result.get("final_status"),
                "orchestration_mode": result.get("orchestration_mode"),
                "task_result_packet": result.get("task_result_packet"),
            },
        })
        print("\nALL_CHECKS_PASSED")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
