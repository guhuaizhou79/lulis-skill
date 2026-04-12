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
        _assert(coding_result.get("coding_executor_result") is None, "code task without repo_path should not force delegated coding executor")

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
        _assert(failing_result.get("normalized_status") in {"needs_replan", "blocked", "failed"}, "failed coding validation should not remain completed")
        _assert(failing_result.get("normalized_status") != "completed", "failed coding validation must not remain completed")
        _assert(failing_result.get("writeback_policy", {}).get("should_write_summary") is False, "failed coding validation should not write summary")
        _assert(failing_result.get("writeback_policy", {}).get("should_write_state") is True, "failed coding validation should recommend state sync")

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
                "run_id": failing_result.get("run_id"),
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
