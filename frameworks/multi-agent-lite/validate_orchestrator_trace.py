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


def main() -> None:
    source_root = Path(__file__).resolve().parent
    temp_dir = Path(tempfile.mkdtemp(prefix="multi-agent-lite-orchestrator-verify-"))
    test_root = temp_dir / "multi-agent-lite"
    shutil.copytree(source_root, test_root)

    try:
        orch = Orchestrator(test_root)
        task = orch.create_task(
            title="verify orchestrator trace output",
            goal="ensure task-level collaboration emits observable trace artifacts",
            task_type="framework_design",
            priority="high",
            acceptance=[
                "task file created",
                "subtasks can be planned",
                "subtasks can be dispatched with models",
                "execution writes a trace event",
                "review writes a trace event",
            ],
        )
        task_id = task["task_id"]
        _assert(task.get("orchestrator_trace_path"), "create_task should materialize orchestrator trace path")
        trace_path = Path(task["orchestrator_trace_path"])
        _assert(trace_path.exists(), "trace file should exist right after task creation")

        task = orch.plan_task(task_id)
        task = orch.dispatch_task(task_id)
        task = orch.execute_task(task_id)
        task = orch.review_task(task_id)

        trace_path = Path(task.get("orchestrator_trace_path") or "")
        _assert(trace_path.exists(), "reviewed task should keep orchestrator trace path")
        rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        events = [row.get("event") for row in rows]
        _assert("task_created" in events, "trace should include task_created")
        _assert("plan_built" in events, "trace should include plan_built")
        _assert("task_dispatched" in events, "trace should include task_dispatched")
        _assert("execution_completed" in events, "trace should include execution_completed")
        _assert("review_completed" in events, "trace should include review_completed")
        _assert(any(isinstance(row.get("snapshot"), dict) for row in rows), "trace rows should include task snapshots")
        _assert(rows[-1].get("snapshot", {}).get("status") == task.get("status"), "last trace snapshot should match final task status")
        _assert(rows[-1].get("snapshot", {}).get("last_review", {}).get("decision") == (task.get("last_review") or {}).get("decision"), "trace snapshot should carry last review summary")

        registry_path = test_root / "runtime" / "orchestrator" / "registry.jsonl"
        _assert(registry_path.exists(), "orchestrator registry should exist")
        registry_rows = [json.loads(line) for line in registry_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        _assert(len(registry_rows) >= len(rows), "registry should record orchestrator events")
        _assert(any(row.get("task_id") == task_id for row in registry_rows), "registry should include current task")
        _assert(any(row.get("trace_path") == str(trace_path) for row in registry_rows), "registry rows should point to trace artifact")

        _print("orchestrator trace status", {
            "task_id": task_id,
            "final_status": task.get("status"),
            "trace_path": str(trace_path),
            "event_count": len(rows),
            "events": events,
            "last_snapshot": rows[-1].get("snapshot"),
            "registry_path": str(registry_path),
        })
        print("\nALL_CHECKS_PASSED")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
