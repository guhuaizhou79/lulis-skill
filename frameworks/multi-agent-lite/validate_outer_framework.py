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
        _assert(direct_result.get("normalized_status") == "completed", "direct route should normalize to completed")
        _assert(direct_result.get("route_explanation"), "direct route should include route explanation")
        _assert(direct_result.get("run_id"), "direct route should expose run_id")
        _assert(isinstance(direct_result.get("run_trace"), dict), "direct route should expose run_trace")
        _assert(isinstance(direct_result.get("task_result_packet"), dict), "direct route should expose task_result_packet")
        _assert(isinstance(direct_result.get("raw_task"), dict), "direct route should expose raw_task snapshot")
        _assert(direct_result.get("raw_task", {}).get("orchestration_mode") == "direct", "direct raw task should record orchestration mode")

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
        _assert(light_result.get("normalized_status") == "completed", "light route should normalize to completed")
        _assert(isinstance(light_result.get("task_result_packet"), dict), "light route should expose task_result_packet")
        _assert(isinstance(light_result.get("raw_task"), dict), "light route should expose raw_task snapshot")
        _assert(light_result.get("raw_task", {}).get("orchestration_mode") == "light_role_check", "light raw task should record orchestration mode")

        coding_payload = {
            "title": "implement repo-aware coding lane",
            "goal": "add coding-specific result structure for staged code work",
            "task_type": "code",
            "priority": "high",
            "acceptance": [
                "produce delivery-ready artifact",
                "include coding-specific result packet",
                "keep outer writeback advisory-only",
            ],
        }
        coding_result = run_outer_framework(test_root, coding_payload)
        _assert(coding_result.get("route") == "multi_agent_lite", "code task should route to staged path")
        _assert(isinstance(coding_result.get("coding_result_packet"), dict), "code task should expose coding_result_packet")
        _assert(isinstance(coding_result.get("coding_result_packet", {}).get("repo_context"), dict), "coding result should include repo_context")
        _assert(isinstance(coding_result.get("coding_result_packet", {}).get("repo_context", {}).get("repo_context"), dict), "coding result should include nested repo-aware context")
        _assert(coding_result.get("manager_sendback_packet") is None, "successful coding run should not emit manager sendback packet")

        failing_repo = test_root / "failing-code-repo"
        failing_repo.mkdir(parents=True, exist_ok=True)
        (failing_repo / "README.md").write_text("hello old world\n", encoding="utf-8")
        (failing_repo / "check.py").write_text("import sys; sys.exit(1)\n", encoding="utf-8")
        failing_payload = {
            "title": "failing coding validation",
            "goal": "exercise outer review mapping for coding validation failure",
            "task_type": "code",
            "priority": "high",
            "repo_path": str(failing_repo),
            "files_of_interest": ["README.md"],
            "allowed_actions": ["read", "replace", "validate"],
            "replace_old": "hello old world",
            "replace_new": "hello new world",
            "validation_commands": ["python3 check.py"],
            "acceptance": [
                "run validation",
                "surface non-completed outer status when validation fails",
                "keep writeback advisory-only",
            ],
        }
        failing_result = run_outer_framework(test_root, failing_payload)
        _assert(failing_result.get("route") == "multi_agent_lite", "failing code task should still route to staged path")
        _assert(isinstance(failing_result.get("coding_executor_result", {}).get("review_packet"), dict), "failing code task should expose coding review packet")
        _assert(failing_result.get("coding_executor_result", {}).get("review_packet", {}).get("verdict") == "needs_replan", "failed validation should emit needs_replan review verdict")
        _assert(isinstance(failing_result.get("manager_sendback_packet"), dict), "failed coding run should emit manager sendback packet")
        _assert(failing_result.get("manager_sendback_packet", {}).get("requested_action") == "replan", "failed validation should request replan sendback")
        _assert(failing_result.get("manager_sendback_packet", {}).get("file_handling") == "keep_changed_files_for_review", "failed validation should keep changed files for manager review")
        _assert(failing_result.get("manager_sendback_packet", {}).get("sendback_count") == 1, "first failing run should start sendback count at 1")
        _assert(isinstance(failing_result.get("sendback_history"), list) and len(failing_result.get("sendback_history") or []) == 1, "first failing run should record one sendback history row")
        _assert(failing_result.get("sendback_history_path"), "failing run should expose sendback history path")
        _assert(Path(failing_result.get("sendback_history_path")).exists(), "sendback history file should exist")
        _assert(isinstance(failing_result.get("next_executor_payload"), dict), "failed coding run should emit next executor payload draft")
        _assert(failing_result.get("next_executor_payload", {}).get("sendback_context", {}).get("verdict") == "needs_replan", "next payload should carry sendback verdict context")
        _assert("README.md" in (failing_result.get("next_executor_payload", {}).get("files_of_interest") or []), "next payload should tighten around changed files when available")
        _assert(isinstance(failing_result.get("rerun_gate"), dict), "failed coding run should expose rerun gate")
        _assert(failing_result.get("rerun_gate", {}).get("eligible") is True, "validation-backed replan should be eligible for rerun gating")
        _assert(failing_result.get("rerun_gate", {}).get("decision") == "allow_rerun", "first narrowed replan should allow rerun")
        _assert(isinstance(failing_result.get("rerun_request"), dict), "eligible rerun should emit rerun request object")
        _assert(failing_result.get("rerun_request", {}).get("request_mode") == "ready", "first rerun request should be ready for executor consumption")
        _assert(isinstance(failing_result.get("rerun_dispatch"), dict), "ready rerun request should emit dispatch artifact")
        _assert(failing_result.get("rerun_dispatch", {}).get("status") == "ready_for_executor_dispatch", "first rerun dispatch should be ready for executor dispatch")
        _assert(Path(failing_result.get("rerun_dispatch", {}).get("path")).exists(), "rerun dispatch artifact should exist on disk")
        _assert(failing_result.get("normalized_status") in {"needs_replan", "blocked", "failed"}, "failed coding validation should not remain completed")
        _assert(failing_result.get("normalized_status") != "completed", "failed coding validation must not remain completed")
        _assert(failing_result.get("writeback_policy", {}).get("should_write_summary") is False, "failed coding validation should not write summary")
        _assert(failing_result.get("writeback_policy", {}).get("should_write_state") is True, "failed coding validation should recommend state sync")

        failing_result_second = run_outer_framework(test_root, failing_payload)
        _assert(failing_result_second.get("manager_sendback_packet", {}).get("sendback_count") == 2, "second failing run should increment sendback count")
        _assert(len(failing_result_second.get("sendback_history") or []) == 2, "second failing run should append sendback history")
        _assert(isinstance(failing_result_second.get("next_executor_payload"), dict), "second failing run should still emit next executor payload draft")
        _assert(failing_result_second.get("next_executor_payload", {}).get("builder_meta", {}).get("repeated_same_verdict") is True, "second failing run should detect repeated same-verdict pattern")
        _assert(isinstance(failing_result_second.get("rerun_gate"), dict), "second failing run should still expose rerun gate")
        _assert(failing_result_second.get("rerun_gate", {}).get("decision") == "review_then_rerun", "repeated sendback should require manager review before rerun")
        _assert(failing_result_second.get("rerun_gate", {}).get("manager_review_required") is True, "repeated sendback should set manager review gate")
        _assert(isinstance(failing_result_second.get("rerun_request"), dict), "review-gated rerun should still emit formal rerun request")
        _assert(failing_result_second.get("rerun_request", {}).get("request_mode") == "await_manager_review", "repeated sendback rerun request should wait for manager review")
        _assert(isinstance(failing_result_second.get("rerun_dispatch"), dict), "review-gated rerun should still emit dispatch artifact")
        _assert(failing_result_second.get("rerun_dispatch", {}).get("status") == "awaiting_manager_review", "review-gated rerun dispatch should await manager review")
        _assert(Path(failing_result_second.get("rerun_dispatch", {}).get("path")).exists(), "review-gated rerun dispatch artifact should exist on disk")

        blocked_repo = test_root / "blocked-code-repo"
        blocked_repo.mkdir(parents=True, exist_ok=True)
        (blocked_repo / "README.md").write_text("hello old world\n", encoding="utf-8")
        blocked_payload = {
            "title": "blocked coding validation",
            "goal": "exercise blocked review mapping for coding validation gating",
            "task_type": "code",
            "priority": "high",
            "repo_path": str(blocked_repo),
            "files_of_interest": ["README.md"],
            "allowed_actions": ["read", "replace", "validate"],
            "replace_old": "hello old world",
            "replace_new": "hello blocked world",
            "validation_commands": ["echo blocked command not allowed"],
            "acceptance": [
                "surface blocked outer status when validation command is unsafe",
                "emit review-first change disposition policy",
            ],
        }
        blocked_result = run_outer_framework(test_root, blocked_payload)
        _assert(blocked_result.get("normalized_status") == "blocked", "unsafe validation command should map to blocked")
        _assert(isinstance(blocked_result.get("change_disposition_policy"), dict), "blocked run should expose change disposition policy")
        _assert(blocked_result.get("change_disposition_policy", {}).get("decision") == "review_then_revert_or_keep", "blocked run with changed files should require revert-or-keep review")
        _assert(isinstance(blocked_result.get("rerun_gate"), dict), "blocked run should still expose rerun gate")
        _assert(blocked_result.get("rerun_gate", {}).get("eligible") is False, "blocked run without safe validation should hold rerun")

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
        _assert(staged_result.get("route_explanation"), "staged route should include route explanation")
        _assert(staged_result.get("normalized_status") in {"completed", "needs_execution_rerun", "needs_replan", "blocked"}, "staged route should expose normalized status")
        _assert(isinstance(staged_result.get("writeback_policy"), dict), "staged route should expose writeback policy stub")
        _assert(staged_result.get("writeback_policy", {}).get("advisory_only") is True, "writeback policy should remain advisory only")
        _assert(isinstance(staged_result.get("writeback_plan"), dict), "staged route should expose writeback plan")
        _assert(staged_result.get("writeback_plan", {}).get("advisory_only") is True, "writeback plan should remain advisory only")
        _assert(isinstance(staged_result.get("writeback_stub"), dict), "staged route should expose writeback stub artifact")
        _assert(staged_result.get("writeback_stub", {}).get("path"), "writeback stub should expose materialized path")
        _assert(Path(staged_result.get("writeback_stub", {}).get("path")).exists(), "writeback stub artifact should exist on disk")
        _assert(Path(staged_result.get("writeback_stub", {}).get("registry")).exists(), "writeback registry should exist on disk")
        _assert(staged_result.get("run_id"), "staged route should expose run_id")
        _assert(isinstance(staged_result.get("run_trace"), dict), "staged route should expose run_trace")

        registry_path = test_root / "runtime" / "outer" / "registry.jsonl"
        _assert(registry_path.exists(), "outer registry should be materialized on disk")
        rows = [json.loads(line) for line in registry_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        _assert(len(rows) >= 3, "outer registry should record each run")
        _assert(any(row.get("run_id") == staged_result.get("run_id") for row in rows), "registry should include staged run trace")

        _print("outer framework status", {
            "direct": {
                "route": direct_result.get("route"),
                "final_status": direct_result.get("final_status"),
                "normalized_status": direct_result.get("normalized_status"),
                "summary": direct_result.get("summary"),
                "route_explanation": direct_result.get("route_explanation"),
                "task_result_packet": direct_result.get("task_result_packet"),
                "raw_task": direct_result.get("raw_task"),
                "run_id": direct_result.get("run_id"),
            },
            "light": {
                "route": light_result.get("route"),
                "final_status": light_result.get("final_status"),
                "normalized_status": light_result.get("normalized_status"),
                "summary": light_result.get("summary"),
                "route_explanation": light_result.get("route_explanation"),
                "task_result_packet": light_result.get("task_result_packet"),
                "raw_task": light_result.get("raw_task"),
                "run_id": light_result.get("run_id"),
            },
            "coding": {
                "route": coding_result.get("route"),
                "normalized_status": coding_result.get("normalized_status"),
                "coding_result_packet": coding_result.get("coding_result_packet"),
                "coding_executor_result": coding_result.get("coding_executor_result"),
                "run_id": coding_result.get("run_id"),
            },
            "coding_failure": {
                "route": failing_result.get("route"),
                "normalized_status": failing_result.get("normalized_status"),
                "writeback_policy": failing_result.get("writeback_policy"),
                "coding_executor_result": failing_result.get("coding_executor_result"),
                "coding_review_packet": failing_result.get("coding_executor_result", {}).get("review_packet"),
                "manager_sendback_packet": failing_result.get("manager_sendback_packet"),
                "next_executor_payload": failing_result.get("next_executor_payload"),
                "rerun_gate": failing_result.get("rerun_gate"),
                "rerun_request": failing_result.get("rerun_request"),
                "rerun_dispatch": failing_result.get("rerun_dispatch"),
                "sendback_history": failing_result.get("sendback_history"),
                "sendback_history_path": failing_result.get("sendback_history_path"),
                "run_id": failing_result.get("run_id"),
            },
            "coding_failure_second": {
                "normalized_status": failing_result_second.get("normalized_status"),
                "manager_sendback_packet": failing_result_second.get("manager_sendback_packet"),
                "next_executor_payload": failing_result_second.get("next_executor_payload"),
                "rerun_gate": failing_result_second.get("rerun_gate"),
                "rerun_request": failing_result_second.get("rerun_request"),
                "rerun_dispatch": failing_result_second.get("rerun_dispatch"),
                "change_disposition_policy": failing_result_second.get("change_disposition_policy"),
                "sendback_history": failing_result_second.get("sendback_history"),
                "sendback_history_path": failing_result_second.get("sendback_history_path"),
                "run_id": failing_result_second.get("run_id"),
            },
            "coding_blocked": {
                "route": blocked_result.get("route"),
                "normalized_status": blocked_result.get("normalized_status"),
                "manager_sendback_packet": blocked_result.get("manager_sendback_packet"),
                "rerun_gate": blocked_result.get("rerun_gate"),
                "change_disposition_policy": blocked_result.get("change_disposition_policy"),
                "run_id": blocked_result.get("run_id"),
            },
            "staged": {
                "route": staged_result.get("route"),
                "final_status": staged_result.get("final_status"),
                "normalized_status": staged_result.get("normalized_status"),
                "summary": staged_result.get("summary"),
                "route_explanation": staged_result.get("route_explanation"),
                "task_shape": staged_result.get("task_shape"),
                "writeback_policy": staged_result.get("writeback_policy"),
                "writeback_plan": staged_result.get("writeback_plan"),
                "writeback_stub": staged_result.get("writeback_stub"),
                "run_id": staged_result.get("run_id"),
            },
            "registry_path": str(registry_path),
            "registry_rows": rows,
        })
        print("\nALL_CHECKS_PASSED")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
