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

    def _envelope(
        self,
        *,
        summary: str,
        changes: list[str] | None = None,
        artifacts: list[str] | None = None,
        risks: list[str] | None = None,
        unknowns: list[str] | None = None,
        next_suggestion: str = "",
        transport_error: bool = False,
        protocol_error: bool = False,
        semantic_error: bool = False,
        raw_excerpt: str = "",
    ) -> Dict[str, Any]:
        return {
            "summary": summary,
            "changes": changes or [],
            "artifacts": artifacts or [],
            "risks": risks or [],
            "unknowns": unknowns or [],
            "next_suggestion": next_suggestion,
            "transport_error": transport_error,
            "protocol_error": protocol_error,
            "semantic_error": semantic_error,
            "raw_excerpt": raw_excerpt,
        }

    def _normalize_result(self, parsed: Dict[str, Any], raw_excerpt: str) -> Dict[str, Any]:
        result = self._envelope(
            summary=str(parsed.get("summary", "")).strip(),
            changes=list(parsed.get("changes") or []),
            artifacts=list(parsed.get("artifacts") or []),
            risks=list(parsed.get("risks") or []),
            unknowns=list(parsed.get("unknowns") or []),
            next_suggestion=str(parsed.get("next_suggestion", "")).strip(),
            transport_error=bool(parsed.get("transport_error", False)),
            protocol_error=bool(parsed.get("protocol_error", False)),
            semantic_error=bool(parsed.get("semantic_error", False)),
            raw_excerpt=raw_excerpt,
        )

        meaningful = any([
            result["summary"],
            result["changes"],
            result["artifacts"],
            result["risks"],
            result["unknowns"],
            result["next_suggestion"],
        ])
        if not meaningful:
            result["semantic_error"] = True
            result["summary"] = "executor returned an empty semantic payload"
            result["next_suggestion"] = "tighten task objective or improve executor prompt"

        return result

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
            '{"summary":"...","changes":["..."],"artifacts":["..."],"risks":["..."],"unknowns":["..."],"next_suggestion":"...","transport_error":false,"protocol_error":false,"semantic_error":false,"raw_excerpt":"..."}'
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

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.timeout + 30,
                env=env,
            )
        except subprocess.TimeoutExpired as e:
            return self._envelope(
                summary="openclaw executor timeout",
                risks=[f"Execution timed out after {self.timeout + 30} seconds"],
                next_suggestion="increase timeout or optimize subtask",
                transport_error=True,
                raw_excerpt=str(e)[:500],
            )
        except Exception as e:
            return self._envelope(
                summary=f"openclaw executor crashed: {str(e)}",
                risks=[str(e)],
                next_suggestion="check executor environment or fallback to mock",
                transport_error=True,
                raw_excerpt=str(e)[:500],
            )

        def safe_decode(b: bytes | None) -> str:
            if not b:
                return ""
            try:
                return b.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return b.decode("gbk")
                except UnicodeDecodeError:
                    return b.decode("utf-8", errors="replace")

        stdout = safe_decode(proc.stdout).strip()
        stderr = safe_decode(proc.stderr).strip()
        raw_excerpt = (stdout or stderr)[:1000]

        if proc.returncode != 0:
            return self._envelope(
                summary="openclaw executor failed",
                risks=[raw_excerpt or "executor error"],
                next_suggestion="fallback to mock executor or inspect runtime",
                transport_error=True,
                raw_excerpt=raw_excerpt,
            )

        parsed = extract_json_object(stdout)
        if parsed is not None:
            return self._normalize_result(parsed, raw_excerpt)

        return self._envelope(
            summary="openclaw executor returned non-json",
            risks=[raw_excerpt],
            next_suggestion="tighten prompt or improve parser",
            protocol_error=True,
            raw_excerpt=raw_excerpt,
        )
