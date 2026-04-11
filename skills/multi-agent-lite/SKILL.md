---
name: multi-agent-lite
description: Use when the user explicitly wants a lightweight multi-agent collaboration workflow in OpenClaw, asks for staged orchestration (manager / research / execution / reviewer), or the task is complex enough that planning, execution, and review should be separated. Do not use for simple one-turn tasks, casual Q&A, or high-risk external actions without a safe staged path.
---

# Multi-Agent Lite

Use this skill only when staged orchestration adds real value over a direct single-agent response.

## Route into this skill when

Trigger when the user clearly wants one of these patterns:
- 多 agent / 多智能体协同
- 按 manager / research / execution / reviewer 的链路推进
- 先规划、再执行、再 review 的阶段化流程
- 需要更强的任务拆分、分派、审查、回退机制
- 需要 review 驱动的 sendback / rerun，而不是单次直出
- 需要 task-level compact result packet 作为外层收敛对象

### Preferred outer routing position

At the outer framework layer, treat this skill as the **staged path**, not the default path.

Recommended route families:
- `direct`
- `light_role_check`
- `multi_agent_lite`

Only route into `multi_agent_lite` when staged orchestration is actually justified.

## Do not route into this skill when

Stay in single-agent mode when any of these is true:
- the task is small enough to finish well in one direct turn
- the work is mostly casual Q&A or lightweight discussion
- splitting roles adds ceremony but not clarity or quality
- the task requires external risky actions and no safe staged approval path exists

## Why use it

Use `multi-agent-lite` to gain four things:
- clearer task decomposition
- explicit role ownership
- review before declaring completion
- auditable send-back when output is not ready

This skill improves orchestration discipline. It does **not** by itself guarantee business correctness, production safety, or domain truth.

## Completion standard

Treat the workflow as complete only when all of the following are true:
- the task has a usable task-level deliverable, not only subtask fragments
- the deliverable materially addresses the original goal
- acceptance items were checked with evidence where possible
- unresolved risks and unknowns are stated plainly
- review decides `approved`

If those conditions are not met, send the task back instead of declaring success.

## Operating rules

- Prefer the existing framework path instead of inventing an ad-hoc parallel orchestration flow.
- Keep the role set lean unless there is a strong reason to expand it.
- Prefer understandable serial orchestration over unnecessary concurrency.
- Be explicit when choosing **not** to use multi-agent mode.
- If runtime or executor quality is degraded, say so plainly and downgrade the promise.
- Prefer frameworks/multi-agent-lite's local materializing mock path over pretending external multi-agent runtime is available when ACP / executor backends are down.
- Identify task shape early. For fact lookup / path lookup / choice answering / config authoring, prefer the required answer form first, then explanation — do not replace the requested output with generic methodology.

## Read only when needed

- `references/framework-status.md` → current maturity, limitations, and interpretation
- `references/repo-layout.md` → repo boundaries and file ownership
- `references/project-usage-guide.md` → project-facing usage guidance

## Current runtime notes

Current runtime already includes:
- structured handoff packets
- task-level `task_result_packet`
- review gap classification and routing hints
- selective execution rerun after review
- stale / active evidence split
- `artifact_lifecycle` tracking
- unified validation entrypoint
- outer adapter shim at `frameworks/multi-agent-lite/outer_adapter.py`

Do not describe this as a purely conceptual prototype anymore. It is still lightweight and bounded, but key first-cut runtime behaviors are already implemented.

## Validation

Primary validation:

```bash
python3 frameworks/multi-agent-lite/validate_delivery.py
```

Outer adapter validation:

```bash
python3 frameworks/multi-agent-lite/validate_outer_adapter.py
```

Backward-compatible wrapper:

```bash
python3 frameworks/multi-agent-lite/validate_handoff_and_result_packet.py
```

## Integration boundary

If an outer framework consumes this runtime, prefer reading:
- `task_result_packet`
- `final_status`
- `orchestration_mode`
- `degrade_history`
- `artifact_lifecycle`

Treat `writeback_hint` / `writeback_recommendation` as advisory only.
Outer framework remains the final authority for memory/docs/state writes.
