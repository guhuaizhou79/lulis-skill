from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class MockExecutor:
    def __init__(self, artifact_root: Path | None = None) -> None:
        self.artifact_root = artifact_root

    def _write_artifact(self, relative_path: str, task: Dict[str, Any], summary: str, changes: list[str]) -> None:
        if self.artifact_root is None:
            return
        target = self.artifact_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join([
            f"# Deliverable for {task.get('task_id')}",
            "",
            f"Title: {task.get('title')}",
            f"Goal: {task.get('goal')}",
            "",
            f"Summary: {summary}",
            "",
            "Changes:",
            *[f"- {item}" for item in changes],
        ])
        target.write_text(content, encoding="utf-8")

    def run(self, role: str, subtask: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        objective = subtask.get("objective", "")
        acceptance = [str(x) for x in task.get("acceptance") or []]
        wants_real_deliverable = any("artifact" in item.lower() or "deliverable" in item.lower() for item in acceptance)

        if role == "research":
            return {
                "summary": f"researched context for: {task.get('title')}",
                "changes": ["collected constraints", "summarized goal"],
                "artifacts": [],
                "risks": [],
                "unknowns": [],
                "next_suggestion": f"handoff to next role with objective: {objective}",
            }
        if role in {"execution_code", "execution_general"}:
            artifacts: list[str] = []
            changes = ["built first-pass output"]
            summary = f"produced draft deliverable for: {task.get('title')}"
            if wants_real_deliverable:
                artifact_rel = f"artifacts/{task.get('task_id', 'task').lower()}-deliverable.md"
                artifacts = [artifact_rel]
                changes.append("materialized task-level deliverable artifact")
                summary = f"produced delivery-ready artifact for: {task.get('title')}"
                self._write_artifact(artifact_rel, task, summary, changes)
            return {
                "summary": summary,
                "changes": changes,
                "artifacts": artifacts,
                "risks": ["still mock execution"],
                "unknowns": [],
                "next_suggestion": "send to reviewer",
            }
        if role == "reviewer":
            return {
                "summary": f"review prepared for: {task.get('title')}",
                "changes": ["checked assigned models and dispatch readiness"],
                "artifacts": [],
                "risks": [],
                "unknowns": [],
                "next_suggestion": "apply review decision",
            }
        return {
            "summary": f"no-op executor result for role {role}",
            "changes": [],
            "artifacts": [],
            "risks": [],
            "unknowns": ["unknown role"],
            "next_suggestion": "inspect routing",
        }
