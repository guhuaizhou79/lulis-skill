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


def run_matrix_scenarios(root: Path) -> None:
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
            "goal": "verify failed execution is sent back to selective execution rerun",
            "task_type": "framework_design",
            "acceptance": [
                "semantic validation passes",
                "task-level deliverable artifact exists",
            ],
            "inject_failure": "semantic_error",
            "expect_status": "READY",
            "expect_decision": "changes_requested",
        },
        {
            "name": "choice-answering-shape",
            "title": "choice answering task",
            "goal": "answer the multiple-choice question directly, then explain",
            "task_type": "choice_answering",
            "acceptance": [
                "explicit option is given first",
                "reason follows the option",
            ],
            "expect_status": "DONE",
            "expect_decision": "approved",
        },
        {
            "name": "path-lookup-shape",
            "title": "path lookup task",
            "goal": "return the exact file path and identifier",
            "task_type": "path_lookup",
            "acceptance": [
                "exact path is returned",
                "exact identifier is returned",
            ],
            "expect_status": "DONE",
            "expect_decision": "approved",
        },
        {
            "name": "strict-review-missing-recommended-contract",
            "title": "strict review contract gap task",
            "goal": "verify strict review sends contract-gap execution back to rerun when recommended contract fields are missing",
            "task_type": "framework_design",
            "acceptance": [
                "execution result echoes the objective",
                "execution result returns acceptance checks",
                "execution result states completion basis",
            ],
            "mutate_execution_result": "drop_recommended_fields",
            "expect_status": "READY",
            "expect_decision": "changes_requested",
        },
        {
            "name": "acceptance-evidence-not-overclaimed",
            "title": "acceptance evidence should stay conservative",
            "goal": "verify acceptance mapping does not overclaim pass from generic delivery text alone",
            "task_type": "framework_design",
            "acceptance": [
                "execution result echoes the objective",
                "execution result returns acceptance checks",
                "execution result states completion basis",
            ],
            "mutate_execution_result": "drop_recommended_fields",
            "expect_status": "READY",
            "expect_decision": "changes_requested",
            "expect_acceptance_statuses": ["unknown", "unknown", "unknown"],
        },
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

        if scenario.get("mutate_execution_result") == "drop_recommended_fields":
            for st in task.get("subtasks", []):
                if st.get("assigned_role") in {"execution_code", "execution_general"}:
                    result = st.get("result") or {}
                    result["objective_echo"] = ""
                    result["acceptance_checks"] = []
                    result["completion_basis"] = []
                    st["result"] = result
            orch.store.save(task)

        task = orch.review_task(task["task_id"])
        decision = (task.get("last_review") or {}).get("decision")
        status = task.get("status")
        artifact_files = [root / path for path in task.get("deliverables", []) if str(path).startswith("artifacts/")]
        artifact_exists = [path.exists() for path in artifact_files]

        acceptance_results = (task.get("last_review") or {}).get("acceptance_results", [])
        acceptance_statuses = [item.get("status") for item in acceptance_results[1:1 + len(scenario.get("acceptance", []))]]
        expected_acceptance_statuses = scenario.get("expect_acceptance_statuses")
        acceptance_expectation_ok = True if not expected_acceptance_statuses else acceptance_statuses == expected_acceptance_statuses
        passed = status == scenario.get("expect_status") and decision == scenario.get("expect_decision") and acceptance_expectation_ok
        _assert(passed, f"matrix scenario failed: {scenario['name']}")

        results.append({
            "scenario": scenario["name"],
            "task_id": task["task_id"],
            "status": status,
            "expected_status": scenario.get("expect_status"),
            "deliverables": task.get("deliverables", []),
            "delivery_status": task.get("delivery_status"),
            "artifact_files": [str(path) for path in artifact_files],
            "artifact_exists": artifact_exists,
            "acceptance_results": acceptance_results,
            "acceptance_statuses": acceptance_statuses,
            "expected_acceptance_statuses": expected_acceptance_statuses,
            "decision": decision,
            "expected_decision": scenario.get("expect_decision"),
            "passed_expectation": passed,
        })

    _print("matrix scenario status", results)


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


def run_execution_rerun_flow(root: Path) -> None:
    orch = Orchestrator(root)
    task = orch.create_task(
        title="Validate execution rerun track",
        goal="force review to send work back to execution and rerun only affected execution subtasks",
        task_type="automation",
        priority="high",
        acceptance=["materialize at least one deliverable artifact"],
    )
    task_id = task["task_id"]

    task = orch.plan_task(task_id)
    task = orch.dispatch_task(task_id)

    extra_execution = None
    for st in task.get("subtasks", []):
        role = str(st.get("assigned_role") or "")
        if role.startswith("execution_"):
            extra_execution = dict(st)
            extra_execution["subtask_id"] = f"{st.get('subtask_id')}-EXTRA"
            extra_execution["title"] = f"{st.get('title', 'execution')} extra rerun control"
            break
    if extra_execution:
        task["subtasks"].append(extra_execution)
    orch.store.save(task)

    task = orch.execute_task(task_id)

    execution_subtasks = [st for st in task.get("subtasks", []) if str(st.get("assigned_role") or "").startswith("execution_")]
    _assert(len(execution_subtasks) >= 2, "execution rerun flow should have at least two execution subtasks")

    failed_subtask_id = str(execution_subtasks[0].get("subtask_id"))
    original_failed_result = dict(execution_subtasks[0].get("result") or {})
    original_failed_artifacts = list(original_failed_result.get("artifacts") or [])
    for subtask in task.get("subtasks", []):
        if str(subtask.get("subtask_id")) == failed_subtask_id:
            subtask["dispatch_status"] = "failed"
            subtask["result"] = {
                "summary": "execution failed and needs rerun",
                "changes": [],
                "artifacts": original_failed_artifacts,
                "risks": ["forced rerun validation"],
                "unknowns": [],
                "next_suggestion": "rerun execution",
                "transport_error": True,
                "protocol_error": False,
                "semantic_error": False,
                "raw_excerpt": "forced rerun validation",
            }
    task["deliverables"] = []
    task["delivery_summary"] = ""
    task["delivery_changes"] = []
    task["delivery_status"] = "not_delivered"
    orch.store.save(task)

    task = orch.review_task(task_id)
    _assert(task["status"] == "READY", "execution rerun path should send task back to READY")
    _assert(task.get("rerun_execution_only") is True, "task should enter rerun_execution_only mode")

    rerun_flags = {
        str(st.get("subtask_id")): bool(st.get("rerun_needed"))
        for st in task.get("subtasks", [])
        if str(st.get("assigned_role") or "").startswith("execution_")
    }
    _assert(rerun_flags.get(failed_subtask_id) is True, "failed execution subtask should be marked for rerun")
    unaffected = [sid for sid, flagged in rerun_flags.items() if sid != failed_subtask_id]
    _assert(unaffected and all(rerun_flags[sid] is False for sid in unaffected), "unaffected execution subtasks should not be marked for rerun")

    task = orch.execute_task(task_id)
    _assert(task.get("rerun_execution_only") is False, "rerun_execution_only flag should clear after rerun execution")

    internal_evidence = task.get("delivery_internal_evidence") or []
    stale_entries = [item for item in internal_evidence if item.get("state") == "stale"]
    active_entries = [item for item in internal_evidence if item.get("state") == "active"]
    artifact_lifecycle = task.get("artifact_lifecycle") or []
    _assert(any(str(item.get("subtask_id")) == failed_subtask_id for item in stale_entries), "failed execution subtask should retain stale evidence record")
    _assert(all(str(item.get("subtask_id")) != failed_subtask_id or item.get("state") == "active" for item in task.get("delivery_evidence") or []), "public delivery evidence should expose only active entries")
    _assert(active_entries, "internal evidence should still include active entries after rerun")
    _assert(any(row.get("state") == "stale" and str(row.get("subtask_id")) == failed_subtask_id for row in artifact_lifecycle), "artifact lifecycle should retain stale artifact rows for rerun subtask")
    _assert(any(row.get("state") == "active" for row in artifact_lifecycle), "artifact lifecycle should retain active artifact rows")

    _print("execution rerun flow status", {
        "task_id": task_id,
        "status": task["status"],
        "rerun_execution_only": task.get("rerun_execution_only"),
        "task_result_packet": task.get("task_result_packet"),
        "execution_subtasks": [
            {
                "subtask_id": st.get("subtask_id"),
                "dispatch_status": st.get("dispatch_status"),
                "rerun_needed": st.get("rerun_needed"),
                "rerun_reason": st.get("rerun_reason"),
            }
            for st in task.get("subtasks", [])
            if str(st.get("assigned_role") or "").startswith("execution_")
        ],
    })


def main() -> None:
    source_root = Path(__file__).resolve().parent
    temp_dir = Path(tempfile.mkdtemp(prefix="multi-agent-lite-verify-"))
    test_root = temp_dir / "multi-agent-lite"
    shutil.copytree(source_root, test_root)

    try:
        run_matrix_scenarios(test_root)
        run_success_flow(test_root)
        run_degrade_flow(test_root)
        run_execution_rerun_flow(test_root)
        print("\nALL_CHECKS_PASSED")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
