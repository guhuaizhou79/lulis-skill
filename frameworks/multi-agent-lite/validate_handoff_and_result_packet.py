from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys
import tempfile


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from core.orchestrator import Orchestrator


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _print(label: str, payload) -> None:
    print(f"\n== {label} ==")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)


def run_success_flow(root: Path) -> None:
    orch = Orchestrator(root)
    task = orch.create_task(
        title="Validate handoff and task result packet",
        goal="produce a delivery-ready artifact and expose a compact task result packet",
        task_type="automation",
        priority="high",
        acceptance=["materialize at least one deliverable artifact", "return a compact task-level result summary"],
    )
    task_id = task["task_id"]

    task = orch.plan_task(task_id)
    task = orch.dispatch_task(task_id)
    _assert(all("handoff" in st for st in task["subtasks"]), "every subtask should have a handoff packet")
    _assert(all("budget" in st["handoff"] for st in task["subtasks"]), "handoff should include budget")

    task = orch.execute_task(task_id)
    packet = task.get("task_result_packet")
    _assert(isinstance(packet, dict), "task_result_packet should exist after execution")
    _assert("status" in packet and "summary" in packet, "task_result_packet missing required top-level fields")
    _assert(isinstance(packet.get("evidence_refs"), list), "task_result_packet should expose evidence_refs")

    task = orch.review_task(task_id)
    _assert(task["status"] == "DONE", "successful review flow should end in DONE")
    _assert(task.get("task_result_packet", {}).get("review_verdict") == "approved", "review verdict should be merged into task_result_packet")

    _print("success flow status", {
        "task_id": task_id,
        "status": task["status"],
        "orchestration_mode": task.get("orchestration_mode"),
        "task_result_packet": task.get("task_result_packet"),
    })


def run_degrade_flow(root: Path) -> None:
    orch = Orchestrator(root)
    task = orch.create_task(
        title="Validate degrade track",
        goal="force repeated sendback until degrade history is recorded",
        task_type="framework_design",
        priority="high",
        acceptance=["this acceptance will not be satisfied by empty execution"],
    )
    task_id = task["task_id"]

    task = orch.plan_task(task_id)
    task = orch.dispatch_task(task_id)
    task = orch.execute_task(task_id)

    task["subtasks"] = []
    task["deliverables"] = []
    task["delivery_summary"] = ""
    task["delivery_changes"] = []
    task["delivery_status"] = "not_delivered"
    task["task_result_packet"] = None
    orch.store.save(task)

    task = orch.review_task(task_id)
    _assert(task["status"] == "PLAN", "first failed review should go back to PLAN")
    _assert(task.get("sendback_count") == 1, "sendback_count should increment after failed review")

    task["status"] = "REVIEW"
    orch.store.save(task)
    task = orch.review_task(task_id)
    _assert(task.get("sendback_count") == 2, "sendback_count should increment again on repeated failed review")
    _assert(task.get("degrade_history"), "degrade_history should be populated after reaching threshold")
    _assert(task.get("orchestration_mode") in {"compact", "minimal"}, "orchestration_mode should degrade after threshold")

    _print("degrade flow status", {
        "task_id": task_id,
        "status": task["status"],
        "sendback_count": task.get("sendback_count"),
        "orchestration_mode": task.get("orchestration_mode"),
        "degrade_history": task.get("degrade_history"),
        "task_result_packet": task.get("task_result_packet"),
    })


def main() -> None:
    source_root = Path(__file__).resolve().parent
    temp_dir = Path(tempfile.mkdtemp(prefix="multi-agent-lite-verify-"))
    test_root = temp_dir / "multi-agent-lite"
    shutil.copytree(source_root, test_root)

    try:
        run_success_flow(test_root)
        run_degrade_flow(test_root)
        print("\nALL_CHECKS_PASSED")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
