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
    readme.write_text("# sample repo\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")

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
            "allowed_actions": ["read", "append", "validate"],
            "append_text": "<!-- controlled append marker -->",
            "files_of_interest": ["README.md"],
        }
        result = executor.execute(payload)
        _assert(result.get("status") == "success", "coding executor should succeed for a valid repo task")
        _assert(result.get("repo_path") == str(repo_root), "coding executor should return repo path")
        _assert(isinstance(result.get("deliverables"), list) and result.get("deliverables"), "coding executor should expose deliverables")
        _assert(isinstance(result.get("repo_scan"), dict) and result.get("repo_scan"), "coding executor should expose repo_scan")
        _assert(isinstance(result.get("target_files"), list) and result.get("target_files"), "coding executor should expose target_files")
        _assert(isinstance(result.get("edit_plan"), list) and result.get("edit_plan"), "coding executor should expose edit_plan")
        _assert(isinstance(result.get("draft_artifacts"), list) and result.get("draft_artifacts"), "coding executor should expose draft artifacts")
        _assert(Path(result.get("draft_artifacts")[0]).exists(), "coding executor draft artifact should exist")
        _assert(isinstance(result.get("files_changed"), list) and result.get("files_changed"), "coding executor should perform controlled append change")
        _assert("controlled append marker" in readme.read_text(encoding="utf-8"), "controlled append marker should be written to target file")

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
