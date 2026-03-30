---
name: multi-agent-lite
description: Use when the user wants a lightweight multi-agent collaboration workflow in OpenClaw: task planning, role-based dispatch, execution, review loops, or asks to use the previously defined manager/research/execution/reviewer framework. Best for tasks complex enough to benefit from staged orchestration but not so heavy that a large agent platform is justified.
---

# Multi-Agent Lite

Use this skill when the task should be routed through the lightweight multi-agent framework instead of a single-agent direct response.

## When to use

Trigger when the user asks for any of these patterns:
- 多 agent 协同 / 多智能体协同
- 按之前那套轻量多-agent框架来
- manager / research / execution / reviewer
- 拆任务、分派、执行、review 的链路
- 复杂任务需要阶段化 orchestration

Do **not** use when:
- the task is simple enough for one direct agent turn,
- there is no real benefit from splitting roles,
- the task is mostly casual Q&A,
- external-risk actions need human approval and no safe staged path is defined.

## Core workflow

Route tasks through these stages:

1. `create task`
2. `plan task`
3. `dispatch subtasks`
4. `execute subtasks`
5. `review outcome`
6. `done` or `send back to plan`

## Default roles

Use only these four roles unless the framework is explicitly expanded:
- `manager`
- `research`
- `execution`
- `reviewer`

Keep the framework lean. Do not invent many permanent roles.

## Default model routing

- manager → `gpt-5.4`
- research → `claude-sonnet-4-20250514`
- execution_code → `gpt-5-codex`
- execution_general → `gpt-5.4`
- reviewer → `o3`
- fallback low-cost → `gpt-4o-mini` / `gpt-4.1-mini`

## Execution policy

Prefer the framework's executor adapter instead of inventing ad-hoc multi-agent flows.

Current implementation status:
- the `multi-agent-lite` framework already supports planning / dispatch / execution / review,
- OpenClaw executor integration exists,
- there is still a known Chinese text encoding/display tail in real executor output.

So when using this skill:
- treat the framework as usable,
- but be candid that executor output quality still has a display-layer limitation,
- for final user-facing prose, do one extra sanity pass if real executor output is consumed.

## Files to read when needed

Read these only when needed:
- `references/framework-status.md` → current state, limitations, and next-step guidance
- `references/repo-layout.md` → how the skill repo and framework repo should stay organized

## Operating rules

- Prefer the existing framework path over inventing a parallel one.
- Keep orchestration serial and understandable unless concurrency is truly needed.
- Preserve auditability: task status, subtask assignment, execution result, review result.
- If the task is too small, explicitly choose not to use multi-agent mode.
- If the task is blocked by environment/runtime issues, say so plainly.
