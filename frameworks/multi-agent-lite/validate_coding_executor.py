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
    (repo_root / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    src_dir = repo_root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "main.py").write_text("def main():\n    return 'ok'\n", encoding="utf-8")
    (src_dir / "worker.py").write_text("def work():\n    return 1\n", encoding="utf-8")

    try:
        executor = CodingExecutor(temp_dir)
        payload = {
            "title": "prepare coding execution",
            "goal": "inspect repo and prepare coding execution packet",
            "repo_path": str(repo_root),
            "task_type": "code",
            "acceptance": [
                "identify repo scope",
                "prepare execution result packet",
            ],
            "validation_expectations": [
                "document validation path",
            ],
            "validation_commands": [
                "python3 check.py",
            ],
            "allowed_actions": ["read", "append", "replace", "validate"],
            "append_text": "<!-- controlled append marker -->",
            "replace_old": "hello old world",
            "replace_new": "hello new world",
            "files_of_interest": ["README.md", "GUIDE.md"],
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
        _assert(isinstance(result.get("target_files"), list) and result.get("target_files"), "coding executor should expose target_files")
        _assert(isinstance(result.get("review_packet"), dict), "coding executor should expose formal review packet")
        _assert(result.get("review_packet", {}).get("verdict") == "accepted", "successful coding run should emit accepted review verdict")
        _assert(result.get("review_packet", {}).get("change_scope") == "multi_file", "multi-file coding run should be classified as multi_file")
        _assert(len(result.get("target_files") or []) >= 2, "coding executor should preserve multi-file target list")
        _assert(isinstance(result.get("edit_plan"), list) and result.get("edit_plan"), "coding executor should expose edit_plan")
        _assert(isinstance(result.get("draft_artifacts"), list) and result.get("draft_artifacts"), "coding executor should expose draft artifacts")
        _assert(len(result.get("draft_artifacts") or []) >= 2, "coding executor should materialize per-file draft artifacts")
        _assert(Path(result.get("draft_artifacts")[0]).exists(), "coding executor draft artifact should exist")
        _assert(isinstance(result.get("files_changed"), list) and result.get("files_changed"), "coding executor should perform controlled file change")
        updated = readme.read_text(encoding="utf-8")
        guide_updated = guide.read_text(encoding="utf-8")
        _assert("controlled append marker" in updated, "controlled append marker should be written to README target file")
        _assert("controlled append marker" in guide_updated, "controlled append marker should be written to GUIDE target file")
        _assert("hello new world" in updated, "controlled replace should be written to README target file")
        _assert("hello new world" in guide_updated, "controlled replace should be written to GUIDE target file")
        _assert(any("python3 check.py" == x for x in result.get("tests_run") or []), "validation command should be recorded")
        _assert(any("passed: rc=0" in x for x in result.get("test_results") or []), "validation command should pass")

        materialized = materialize_coding_run(temp_dir, payload)
        _assert(Path(materialized.get("artifact")).exists(), "coding executor should materialize runtime artifact")

        _print("coding executor status", {
            "result": result,
            "artifact": materialized.get("artifact"),
        })
        print("\nALL_CHECKS_PASSED")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
