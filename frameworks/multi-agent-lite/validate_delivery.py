from pathlib import Path
import json
import sys


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    from core.orchestrator import Orchestrator

    orch = Orchestrator(root)

    scenarios = [
        {
            "name": "baseline-prototype",
            "title": "sample task",
            "goal": "prove the lightweight multi-agent skeleton works",
            "task_type": "framework_design",
            "acceptance": [
                "task file created",
                "state can move to PLAN",
                "subtasks can be planned",
                "subtasks can be dispatched with models",
                "subtasks can execute through executor adapter",
                "review loop can finish or send back",
            ],
            "expect_status": "DONE",
            "expect_decision": "approved",
        },
        {
            "name": "deliverable-required",
            "title": "delivery required task",
            "goal": "produce a task-level deliverable artifact and complete review",
            "task_type": "framework_design",
            "acceptance": [
                "task-level deliverable artifact exists",
                "review can verify delivery evidence",
                "delivery summary reflects task artifact",
            ],
            "expect_status": "DONE",
            "expect_decision": "approved",
        },
        {
            "name": "failure-semantic-error",
            "title": "semantic failure task",
            "goal": "verify failed execution is sent back to plan",
            "task_type": "framework_design",
            "acceptance": [
                "semantic validation passes",
                "task-level deliverable artifact exists"
            ],
            "inject_failure": "semantic_error",
            "expect_status": "PLAN",
            "expect_decision": "changes_requested"
        },
        {
            "name": "choice-answering-shape",
            "title": "choice answering task",
            "goal": "answer the multiple-choice question directly, then explain",
            "task_type": "choice_answering",
            "acceptance": [
                "explicit option is given first",
                "reason follows the option"
            ],
            "expect_status": "DONE",
            "expect_decision": "approved"
        },
        {
            "name": "path-lookup-shape",
            "title": "path lookup task",
            "goal": "return the exact file path and identifier",
            "task_type": "path_lookup",
            "acceptance": [
                "exact path is returned",
                "exact identifier is returned"
            ],
            "expect_status": "DONE",
            "expect_decision": "approved"
        }
    ]

    results = []
    for scenario in scenarios:
        task = orch.create_task(
            title=scenario["title"],
            goal=scenario["goal"],
            task_type=scenario["task_type"],
            acceptance=scenario["acceptance"],
        )
        orch.plan_task(task["task_id"])
        orch.dispatch_task(task["task_id"])
        orch.execute_task(task["task_id"])
        task = orch.store.load(task["task_id"])
        materialized_paths = [root / path for path in task.get("deliverables", []) if str(path).startswith("artifacts/")]
        preexisting_paths = [path for path in materialized_paths if path.exists()]

        if scenario.get("inject_failure") == "semantic_error":
            for st in task.get("subtasks", []):
                if st.get("assigned_role") in {"execution_code", "execution_general"}:
                    result = st.get("result") or {}
                    result["semantic_error"] = True
                    result["summary"] = "semantic validation failed"
                    result["artifacts"] = []
                    result["changes"] = []
                    st["result"] = result
            task["artifacts"] = []
            task["deliverables"] = []
            task["deliverable_candidates"] = []
            task["delivery_changes"] = []
            task["delivery_evidence"] = []
            task["delivery_summary"] = ""
            task["delivery_status"] = "not_delivered"
            orch.store.save(task)

        task = orch.review_task(task["task_id"])
        decision = (task.get("last_review") or {}).get("decision")
        status = task.get("status")
        artifact_files = [root / path for path in task.get("deliverables", []) if str(path).startswith("artifacts/")]
        artifact_exists = [path.exists() for path in artifact_files]
        no_artifact_residue = all(not path.exists() for path in materialized_paths) if scenario.get("inject_failure") else None

        results.append({
            "scenario": scenario["name"],
            "task_id": task["task_id"],
            "status": status,
            "expected_status": scenario.get("expect_status"),
            "deliverables": task.get("deliverables", []),
            "delivery_status": task.get("delivery_status"),
            "artifact_files": [str(path) for path in artifact_files],
            "artifact_exists": artifact_exists,
            "acceptance_results": (task.get("last_review") or {}).get("acceptance_results", []),
            "decision": decision,
            "expected_decision": scenario.get("expect_decision"),
            "passed_expectation": status == scenario.get("expect_status") and decision == scenario.get("expect_decision"),
        })

    print(json.dumps(results, ensure_ascii=False, indent=2))
