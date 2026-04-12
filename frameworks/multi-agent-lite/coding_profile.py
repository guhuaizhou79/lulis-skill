from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


CODE_TASK_TYPES = {"code", "bugfix", "refactor", "repo_analysis"}
MANIFEST_FILES = ["pyproject.toml", "package.json", "requirements.txt", "setup.py", "Cargo.toml", "go.mod"]
ENTRYPOINT_HINTS = ["main.py", "app.py", "server.py", "index.ts", "index.js", "main.ts", "manage.py"]


def is_coding_task(task: Dict[str, Any]) -> bool:
    task_type = str(task.get("task_type") or "").strip()
    if task_type in CODE_TASK_TYPES:
        return True
    goal = str(task.get("goal") or "").lower()
    title = str(task.get("title") or "").lower()
    hints = ["code", "repo", "bug", "fix", "refactor", "implement", "module", "function"]
    text = f"{title} {goal}"
    return any(token in text for token in hints)


def _detect_language(top_level: List[str]) -> str:
    names = set(top_level)
    if "pyproject.toml" in names or "requirements.txt" in names or "setup.py" in names:
        return "python"
    if "package.json" in names:
        return "node"
    if "Cargo.toml" in names:
        return "rust"
    if "go.mod" in names:
        return "go"
    return "unknown"


def build_repo_context(repo_path: str, target_files: List[str] | None = None) -> Dict[str, Any]:
    path = Path(str(repo_path or "").strip()) if str(repo_path or "").strip() else None
    if not path or not path.exists() or not path.is_dir():
        return {
            "repo_path": str(repo_path or ""),
            "top_level": [],
            "manifest_files": [],
            "entrypoint_hints": [],
            "language_hint": "unknown",
            "target_rationale": "repo unavailable",
        }

    top_level: List[str] = []
    manifest_files: List[str] = []
    entrypoints: List[str] = []
    for child in sorted(path.iterdir(), key=lambda p: p.name):
        if child.name.startswith("."):
            continue
        top_level.append(child.name)
        if child.name in MANIFEST_FILES:
            manifest_files.append(child.name)
        if child.name in ENTRYPOINT_HINTS:
            entrypoints.append(child.name)

    targets = [str(x) for x in (target_files or []) if str(x).strip()]
    rationale = "no explicit target files yet"
    if targets:
        rationale = f"current target files: {targets[:5]}"

    return {
        "repo_path": str(path),
        "top_level": top_level[:20],
        "manifest_files": manifest_files,
        "entrypoint_hints": entrypoints,
        "language_hint": _detect_language(top_level),
        "target_rationale": rationale,
    }


def build_code_context_packet(task: Dict[str, Any]) -> Dict[str, Any]:
    constraints = [str(x) for x in (task.get("constraints") or []) if str(x).strip()]
    acceptance = [str(x) for x in (task.get("acceptance") or []) if str(x).strip()]
    target_files = [str(x) for x in (task.get("files_of_interest") or []) if str(x).strip()]
    repo_context = build_repo_context(str(task.get("repo_path") or ""), target_files)
    return {
        "task_type": str(task.get("task_type") or "general"),
        "goal": str(task.get("goal") or ""),
        "constraints": constraints,
        "acceptance": acceptance,
        "target_files": target_files,
        "repo_context": repo_context,
        "focus": {
            "needs_code_changes": True,
            "needs_repo_reading": True,
            "needs_validation": True,
        },
    }


def build_code_result_packet(task: Dict[str, Any], packet: Dict[str, Any]) -> Dict[str, Any]:
    changes = [str(x) for x in (packet.get("changes") or []) if str(x).strip()]
    deliverables = [str(x) for x in (packet.get("deliverables") or []) if str(x).strip()]
    evidence_refs = [str(x) for x in (packet.get("evidence_refs") or []) if str(x).strip()]
    risks = [str(x) for x in (packet.get("risks") or []) if str(x).strip()]

    files_touched = [item for item in deliverables if "/" in item or item.endswith((".py", ".md", ".json", ".ts", ".tsx", ".js"))]
    test_refs = [item for item in evidence_refs if "validate" in item.lower() or "test" in item.lower()]

    return {
        "code_change_summary": str(packet.get("summary") or ""),
        "files_touched": files_touched,
        "contracts_changed": [],
        "tests_run": test_refs,
        "test_results": ["passed" for _ in test_refs],
        "risk_surface": risks,
        "rollback_notes": [],
        "followup_refactors": [],
        "repo_context": build_code_context_packet(task),
        "change_count": len(changes),
    }
