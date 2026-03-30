from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from .json_extract import extract_json_object


class OpenClawExecutor:
    def __init__(self, agent_id: str = "main", timeout: int = 180):
        self.agent_id = agent_id
        self.timeout = timeout
        self.command = self._resolve_openclaw_command()

    def _resolve_openclaw_command(self):
        for name in ["openclaw.cmd", "openclaw.exe", "openclaw"]:
            found = shutil.which(name)
            if found:
                return [found]
        npm_bin = Path.home() / "AppData" / "Roaming" / "npm"
        for cand in [npm_bin / "openclaw.cmd", npm_bin / "openclaw.ps1"]:
            if cand.exists():
                if cand.suffix.lower() == ".ps1":
                    return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(cand)]
                return [str(cand)]
        raise FileNotFoundError("openclaw executable not found")

    def build_prompt(self, role: str, subtask: Dict[str, Any], task: Dict[str, Any]) -> str:
        payload = {
            "role": role,
            "task_title": task.get("title"),
            "task_goal": task.get("goal"),
            "objective": subtask.get("objective"),
            "acceptance": task.get("acceptance", []),
            "constraints": task.get("constraints", []),
        }
        return (
            "你是多agent框架中的一个执行角色。"
            "严格只输出 JSON，不要 markdown，不要解释。"
            "JSON 结构必须为: "
            '{"summary":"...","changes":["..."],"artifacts":["..."],"risks":["..."],"unknowns":["..."],"next_suggestion":"..."}'
            f"\n输入任务: {json.dumps(payload, ensure_ascii=False)}"
        )

    def run(self, role: str, subtask: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self.build_prompt(role, subtask, task)
        cmd = self.command + [
            "agent",
            "--local",
            "--agent",
            self.agent_id,
            "--message",
            prompt,
            "--json",
            "--timeout",
            str(self.timeout),
        ]
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout + 30,
            env=env,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if proc.returncode != 0:
            return {
                "summary": "openclaw executor failed",
                "changes": [],
                "artifacts": [],
                "risks": [stdout[:1000] or stderr[:1000] or "executor error"],
                "unknowns": [],
                "next_suggestion": "fallback to mock executor or inspect runtime",
                "executor_error": True,
            }

        parsed = extract_json_object(stdout)
        if parsed is not None:
            return parsed

        return {
            "summary": "openclaw executor returned non-json",
            "changes": [],
            "artifacts": [],
            "risks": [stdout[:1000] or stderr[:1000]],
            "unknowns": [],
            "next_suggestion": "tighten prompt or improve parser",
            "parse_error": True,
        }
