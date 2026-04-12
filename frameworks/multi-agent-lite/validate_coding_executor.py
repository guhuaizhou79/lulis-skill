from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys
import tempfile


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from coding_executor import CodingExecutor, materialize_coding_run


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
    temp_dir = Path(tempfile.mkdtemp(prefix="multi-agent-lite-coding-executor-verify-"))
    repo_root = temp_dir / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    readme = repo_root / "README.md"
    readme.write_text("# sample repo\nhello old world\n", encoding="utf-8")
    guide = repo_root / "GUIDE.md"
    guide.write_text("guide hello old world\n", encoding="utf-8")
    (repo_root / "check.py").write_text("print('ok')\n", encoding="utf-8")
    (repo_root / "test_sample.py").write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    src_dir = repo_root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "main.py").write_text("def main():\n    return 'ok'\n", encoding="utf-8")
    (src_dir / "worker.py").write_text("class Worker:\n    pass\n\ndef reconcile_orders():\n    return 1\n", encoding="utf-8")

    try:
        executor = CodingExecutor(temp_dir)
        payload = {
            "title": "prepare coding execution",
            "goal": "reconcile orders execution path",
            "repo_path": str(repo_root),
            "task_type": "code",
            "acceptance": [
                "identify repo scope",
                "prepare execution result packet",
            ],
            "validation_expectations": [
                "document validation path",
                "capture validation surfaces",
            ],
            "validation_commands": [
                "python3 -m py_compile src/main.py",
                "python3 -c \"import sys; sys.path.insert(0, 'src'); import worker\"",
                "python3 -c \"assert 1 == 1\"",
                "python3 check.py",
            ],
            "allowed_actions": ["read", "append", "replace", "validate"],
            "append_text": "# controlled append marker",
            "replace_old": "hello old world",
            "replace_new": "hello new world",
            "files_of_interest": [],
        }
        result = executor.execute(payload)
        _assert(result.get("status") == "success", "coding executor should succeed for a valid repo task")
        _assert(result.get("repo_path") == str(repo_root), "coding executor should return repo path")
        _assert(isinstance(result.get("deliverables"), list) and result.get("deliverables"), "coding executor should expose deliverables")
        _assert(isinstance(result.get("repo_scan"), dict) and result.get("repo_scan"), "coding executor should expose repo_scan")
        _assert("pyproject.toml" in (result.get("repo_scan", {}).get("manifest_files") or []), "repo scan should expose manifest files")
        _assert("src/main.py" in (result.get("repo_scan", {}).get("entrypoint_hints") or []), "repo scan should expose entrypoint hints")
        _assert("src" in (result.get("repo_scan", {}).get("source_dirs") or []), "repo scan should expose source dirs")
        _assert(result.get("repo_scan", {}).get("language_hint") == "python", "repo scan should infer python language hint")
        _assert(any(x.endswith("worker.py") for x in (result.get("repo_scan", {}).get("discovered_code_files") or [])), "repo scan should discover nested code files")
        _assert(any((row.get("file") == "src/worker.py" and "reconcile_orders" in (row.get("symbols") or [])) for row in (result.get("repo_scan", {}).get("symbol_index") or [])), "repo scan should extract lightweight symbol index")
        _assert(isinstance(result.get("target_files"), list) and result.get("target_files"), "coding executor should expose target_files")
        _assert("src/worker.py" in (result.get("target_files") or []), "goal-aware targeting should include symbol-matched file")
        _assert(isinstance(result.get("review_packet"), dict), "coding executor should expose formal review packet")
        _assert(isinstance(result.get("validation_records"), list) and result.get("validation_records"), "coding executor should expose structured validation records")
        surfaces = [str(x.get("surface") or "") for x in (result.get("validation_records") or [])]
        _assert("syntax" in surfaces, "validation records should include syntax surface")
        _assert("import" in surfaces, "validation records should include import surface")
        _assert("unit" in surfaces, "validation records should include unit surface")
        _assert("project_command" in surfaces, "validation records should include project command surface")
        _assert(isinstance(result.get("review_packet", {}).get("validation_records"), list), "review packet should carry validation records")
        _assert(isinstance(result.get("validation_policy"), dict), "coding result should expose validation policy")
        _assert(result.get("validation_policy", {}).get("verdict_hint") == "accepted", "successful validation surfaces should hint accepted")
        _assert(result.get("review_packet", {}).get("verdict") == "accepted", "successful coding run should emit accepted review verdict")
        _assert(result.get("review_packet", {}).get("change_scope") == "multi_file", "multi-file coding run should be classified as multi_file")
        _assert(len(result.get("target_files") or []) >= 2, "coding executor should preserve multi-file target list")
        _assert(isinstance(result.get("edit_plan"), list) and result.get("edit_plan"), "coding executor should expose edit_plan")
        _assert(any((item.get("file") == "src/worker.py" and "reconcile_orders" in ((item.get("context") or {}).get("goal_symbol_hits") or [])) for item in (result.get("edit_plan") or [])), "edit plan should surface goal symbol hits")
        _assert(isinstance(result.get("draft_artifacts"), list) and result.get("draft_artifacts"), "coding executor should expose draft artifacts")
        _assert(len(result.get("draft_artifacts") or []) >= 2, "coding executor should materialize per-file draft artifacts")
        _assert(Path(result.get("draft_artifacts")[0]).exists(), "coding executor draft artifact should exist")
        _assert(isinstance(result.get("files_changed"), list) and result.get("files_changed"), "coding executor should perform controlled file change")
        worker_updated = (src_dir / "worker.py").read_text(encoding="utf-8")
        main_updated = (src_dir / "main.py").read_text(encoding="utf-8")
        readme_updated = readme.read_text(encoding="utf-8")
        guide_updated = guide.read_text(encoding="utf-8")
        _assert("controlled append marker" in worker_updated or "controlled append marker" in main_updated, "controlled append marker should be written to narrowed active target files")
        _assert("hello new world" not in readme_updated, "symbol-aware targeting should avoid broad replace on README when goal points elsewhere")
        _assert("hello new world" not in guide_updated, "symbol-aware targeting should avoid broad replace on GUIDE when goal points elsewhere")
        _assert(any("python3 check.py" == x for x in result.get("tests_run") or []), "validation command should be recorded")
        _assert(any("passed: rc=0" in x for x in result.get("test_results") or []), "validation command should pass")

        materialized = materialize_coding_run(temp_dir, payload)
        _assert(Path(materialized.get("artifact")).exists(), "coding executor should materialize runtime artifact")

        failing_payload = {
            "title": "validation policy failure case",
            "goal": "reconcile orders execution path",
            "repo_path": str(repo_root),
            "task_type": "code",
            "validation_commands": [
                "python3 -m py_compile broken.py",
                "python3 -c \"import broken\"",
            ],
            "allowed_actions": ["read", "validate"],
            "files_of_interest": ["broken.py"],
        }
        broken_file = repo_root / "broken.py"
        broken_file.write_text("def broken(:\n    pass\n", encoding="utf-8")
        failing_result = materialize_coding_run(temp_dir, failing_payload).get("result") or {}
        _assert(failing_result.get("review_packet", {}).get("verdict") == "needs_replan", "syntax/import failures should map to needs_replan")
        _assert(failing_result.get("validation_policy", {}).get("change_disposition_hint") == "revert_suggested", "syntax/import failures should suggest revert")

        _print("coding executor status", {
            "result": result,
            "failing_result": failing_result,
            "artifact": materialized.get("artifact"),
        })
        print("\nALL_CHECKS_PASSED")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
