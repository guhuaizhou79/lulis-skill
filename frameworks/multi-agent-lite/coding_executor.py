from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import subprocess

from coding_executor_contract import (
    build_coding_task_packet,
    build_coding_result_packet,
    build_empty_coding_result,
)


SAFE_VALIDATE_PREFIXES = (
    "python3 ",
    "python ",
    "pytest",
    "node ",
    "npm test",
    "npm run ",
    "pnpm test",
    "pnpm run ",
    "bash ",
    "sh ",
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

    def _read_preview(self, repo: Path, rel: str, max_chars: int = 600) -> str:
        full = repo / rel
        if not full.exists() or not full.is_file():
            return ""
        try:
            text = full.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "<binary-or-non-utf8>"
        return text[:max_chars]

    def _materialize_draft_artifacts(self, repo: Path, packet: Dict[str, Any], edit_plan: List[Dict[str, Any]]) -> List[str]:
        runtime_dir = self.root / "runtime" / "coding-executor" / "drafts"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        goal = str(packet.get("goal") or "").strip()
        title = str(packet.get("title") or "coding-task").replace(" ", "-").lower()[:50]
        artifacts: List[str] = []
        for idx, item in enumerate(edit_plan, start=1):
            rel = str(item.get("file") or "").strip()
            if not rel:
                continue
            preview = self._read_preview(repo, rel)
            artifact = runtime_dir / f"{title}-{idx:02d}.md"
            artifact.write_text(
                "\n".join([
                    f"# Draft edit plan for {rel}",
                    "",
                    f"Goal: {goal}",
                    f"Intent: {item.get('intent')}",
                    f"Mode: {item.get('mode')}",
                    "",
                    "## Current preview",
                    "```",
                    preview,
                    "```",
                    "",
                    "## Proposed change note",
                    f"Prepare a targeted modification for `{rel}` aligned with the task goal above.",
                ]),
                encoding="utf-8",
            )
            artifacts.append(str(artifact))
        return artifacts

    def _apply_append_change(self, repo: Path, packet: Dict[str, Any], target_files: List[str]) -> tuple[List[str], List[str], List[str]]:
        allowed_actions = {str(x).strip() for x in (packet.get("allowed_actions") or []) if str(x).strip()}
        append_text = str(packet.get("append_text") or "")
        files_changed: List[str] = []
        tests_run: List[str] = []
        test_results: List[str] = []
        if "append" not in allowed_actions or not append_text or not target_files:
            return files_changed, tests_run, test_results

        rel = target_files[0]
        full = repo / rel
        if not full.exists() or not full.is_file():
            return files_changed, tests_run, test_results

        original = full.read_text(encoding="utf-8")
        if append_text not in original:
            sep = "" if original.endswith("\n") else "\n"
            full.write_text(original + sep + append_text, encoding="utf-8")
            files_changed.append(str(full))
            tests_run.append(f"file append applied: {rel}")
            test_results.append("passed")
        else:
            tests_run.append(f"file append skipped (already present): {rel}")
            test_results.append("passed")
        return files_changed, tests_run, test_results

    def _apply_replace_change(self, repo: Path, packet: Dict[str, Any], target_files: List[str]) -> tuple[List[str], List[str], List[str], List[str]]:
        allowed_actions = {str(x).strip() for x in (packet.get("allowed_actions") or []) if str(x).strip()}
        replace_old = str(packet.get("replace_old") or "")
        replace_new = str(packet.get("replace_new") or "")
        files_changed: List[str] = []
        tests_run: List[str] = []
        test_results: List[str] = []
        risks: List[str] = []
        if "replace" not in allowed_actions or not replace_old or not target_files:
            return files_changed, tests_run, test_results, risks

        rel = target_files[0]
        full = repo / rel
        if not full.exists() or not full.is_file():
            return files_changed, tests_run, test_results, risks

        original = full.read_text(encoding="utf-8")
        hits = original.count(replace_old)
        if hits == 0:
            tests_run.append(f"file replace skipped (old text not found): {rel}")
            test_results.append("passed")
            risks.append("replace_old not found; no change applied")
            return files_changed, tests_run, test_results, risks
        if hits > 1:
            tests_run.append(f"file replace blocked (multiple matches): {rel}")
            test_results.append("blocked")
            risks.append("replace_old matched multiple times; exact replace not applied")
            return files_changed, tests_run, test_results, risks

        updated = original.replace(replace_old, replace_new, 1)
        if updated != original:
            full.write_text(updated, encoding="utf-8")
            files_changed.append(str(full))
            tests_run.append(f"file replace applied: {rel}")
            test_results.append("passed")
        return files_changed, tests_run, test_results, risks

    def _run_validation_commands(self, repo: Path, payload: Dict[str, Any]) -> tuple[List[str], List[str], List[str]]:
        commands = [str(x).strip() for x in (payload.get("validation_commands") or []) if str(x).strip()]
        tests_run: List[str] = []
        test_results: List[str] = []
        risks: List[str] = []
        for cmd in commands[:5]:
            if not any(cmd.startswith(prefix) for prefix in SAFE_VALIDATE_PREFIXES):
                tests_run.append(f"validation command blocked: {cmd}")
                test_results.append("blocked")
                risks.append(f"validation command not in safe prefixes: {cmd}")
                continue
            proc = subprocess.run(
                cmd,
                cwd=str(repo),
                shell=True,
                text=True,
                capture_output=True,
                timeout=30,
            )
            tests_run.append(cmd)
            status = "passed" if proc.returncode == 0 else "failed"
            snippet = (proc.stdout or proc.stderr or "").strip()[:160]
            test_results.append(f"{status}: rc={proc.returncode} {snippet}".strip())
            if proc.returncode != 0:
                risks.append(f"validation command failed: {cmd}")
        return tests_run, test_results, risks

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        packet = build_coding_task_packet(payload)
        packet["append_text"] = payload.get("append_text") or ""
        packet["replace_old"] = payload.get("replace_old") or ""
        packet["replace_new"] = payload.get("replace_new") or ""
        repo = self._normalize_repo_path(packet.get("repo_path") or "")
        goal = str(packet.get("goal") or "").strip()

        if not repo or not repo.exists() or not repo.is_dir():
            return build_empty_coding_result(packet, "repo_path is missing or does not exist")
        if not goal:
            return build_empty_coding_result(packet, "goal is missing")

        repo_scan = self._scan_repo(repo)
        target_files = self._candidate_files(repo, packet)
        repo_scan["target_rationale"] = f"selected target files: {target_files[:5]}" if target_files else "no target files selected"
        edit_plan = self._build_edit_plan(packet, target_files)
        draft_artifacts = self._materialize_draft_artifacts(repo, packet, edit_plan)
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

        files_changed, apply_tests, apply_results = self._apply_append_change(repo, packet, target_files)
        replace_changed, replace_tests, replace_results, replace_risks = self._apply_replace_change(repo, packet, target_files)
        files_changed.extend([x for x in replace_changed if x not in files_changed])
        risks.extend(replace_risks)
        tests_run.extend(apply_tests)
        test_results.extend(apply_results)
        tests_run.extend(replace_tests)
        test_results.extend(replace_results)

        validation_tests, validation_results, validation_risks = self._run_validation_commands(repo, payload)
        tests_run.extend(validation_tests)
        test_results.extend(validation_results)
        risks.extend(validation_risks)

        if files_changed:
            summary = f"coding executor applied controlled file change for: {packet['title']}"
        if validation_tests:
            summary += " | validation commands executed"

        result = build_coding_result_packet(
            packet,
            summary=summary,
            files_changed=files_changed,
            target_files=target_files,
            deliverables=deliverables,
            repo_scan=repo_scan,
            edit_plan=edit_plan,
            draft_artifacts=draft_artifacts,
            tests_run=tests_run,
            test_results=test_results,
            risks=risks,
            blockers=[],
            needs_input=[],
            recommended_next_step="manager may now review validation results and decide whether to extend executor beyond controlled edit modes",
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
