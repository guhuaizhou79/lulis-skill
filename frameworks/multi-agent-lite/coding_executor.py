from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

from coding_executor_contract import (
    build_coding_task_packet,
    build_coding_result_packet,
    build_empty_coding_result,
)


class CodingExecutor:
    def __init__(self, root: Path):
        self.root = root

    def _normalize_repo_path(self, repo_path: str) -> Path | None:
        value = str(repo_path or "").strip()
        if not value:
            return None
        path = Path(value)
        if not path.is_absolute():
            path = (self.root / value).resolve()
        return path

    def _scan_repo(self, repo: Path) -> Dict[str, Any]:
        top_files: List[str] = []
        code_files: List[str] = []
        for child in sorted(repo.iterdir(), key=lambda p: p.name):
            if child.name.startswith("."):
                continue
            top_files.append(child.name)
            if child.is_file() and child.suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md"}:
                code_files.append(child.name)
        return {
            "top_level": top_files[:20],
            "code_like_files": code_files[:20],
        }

    def _candidate_files(self, repo: Path, packet: Dict[str, Any]) -> List[str]:
        explicit = [x for x in (packet.get("files_of_interest") or []) if x]
        if explicit:
            return explicit[:8]
        candidates: List[str] = []
        for rel in ["README.md", "pyproject.toml", "package.json", "requirements.txt"]:
            if (repo / rel).exists():
                candidates.append(rel)
        for child in sorted(repo.iterdir(), key=lambda p: p.name):
            if len(candidates) >= 8:
                break
            if child.is_file() and child.suffix in {".py", ".ts", ".tsx", ".js", ".jsx"} and child.name not in candidates:
                candidates.append(child.name)
        return candidates[:8]

    def _build_edit_plan(self, packet: Dict[str, Any], target_files: List[str]) -> List[Dict[str, Any]]:
        goal = str(packet.get("goal") or "").strip()
        plan: List[Dict[str, Any]] = []
        for rel in target_files[:5]:
            plan.append({
                "file": rel,
                "intent": f"inspect and update {rel} in support of: {goal}",
                "mode": "targeted_edit",
            })
        return plan

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        packet = build_coding_task_packet(payload)
        repo = self._normalize_repo_path(packet.get("repo_path") or "")
        goal = str(packet.get("goal") or "").strip()

        if not repo or not repo.exists() or not repo.is_dir():
            return build_empty_coding_result(packet, "repo_path is missing or does not exist")
        if not goal:
            return build_empty_coding_result(packet, "goal is missing")

        repo_scan = self._scan_repo(repo)
        target_files = self._candidate_files(repo, packet)
        edit_plan = self._build_edit_plan(packet, target_files)
        deliverables: List[str] = []
        for rel in target_files:
            full = repo / rel
            if full.exists():
                deliverables.append(str(full))

        summary = f"coding executor prepared repo-scoped execution packet for: {packet['title']}"
        tests_run = [f"validation expectation: {x}" for x in (packet.get("validation_expectations") or [])]
        test_results = ["not_run_yet" for _ in tests_run]
        risks = []
        if not tests_run:
            risks.append("validation path not specified yet")
        if not target_files:
            risks.append("no target files selected yet")

        result = build_coding_result_packet(
            packet,
            summary=summary,
            files_changed=[],
            target_files=target_files,
            deliverables=deliverables,
            repo_scan=repo_scan,
            edit_plan=edit_plan,
            tests_run=tests_run,
            test_results=test_results,
            risks=risks,
            blockers=[],
            needs_input=[],
            recommended_next_step="manager may now choose target files and approve a real edit/apply/validate loop",
        )
        return result


def materialize_coding_run(root: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    runtime_dir = root / "runtime" / "coding-executor"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    executor = CodingExecutor(root)
    result = executor.execute(payload)
    title = str(payload.get("title") or "coding-task").replace(" ", "-").lower()
    artifact = runtime_dir / f"{title[:50]}.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "result": result,
        "artifact": str(artifact),
    }
