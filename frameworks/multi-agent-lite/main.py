from pathlib import Path
import sys
import json


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    from core.orchestrator import Orchestrator

    orch = Orchestrator(root)
    task = orch.create_task(
        title="sample task",
        goal="prove the lightweight multi-agent skeleton works",
        task_type="framework_design",
        acceptance=[
            "task file created",
            "state can move to PLAN",
            "subtasks can be planned",
            "subtasks can be dispatched with models",
            "subtasks can execute through executor adapter",
            "review loop can finish or send back",
        ],
    )
    orch.plan_task(task["task_id"])
    orch.dispatch_task(task["task_id"])
    orch.execute_task(task["task_id"])
    task = orch.review_task(task["task_id"])
    print(json.dumps({
        "task_id": task["task_id"],
        "status": task["status"],
        "dispatch_summary": task.get("dispatch_summary", {}),
        "subtasks": [
            {
                "subtask_id": st.get("subtask_id"),
                "role": st.get("assigned_role"),
                "model": st.get("assigned_model"),
                "dispatch_status": st.get("dispatch_status"),
                "result_summary": (st.get("result") or {}).get("summary"),
            }
            for st in task.get("subtasks", [])
        ],
        "last_review": task.get("last_review", {}),
    }, ensure_ascii=False, indent=2))
