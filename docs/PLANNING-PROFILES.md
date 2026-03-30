# Planning profiles

`multi-agent-lite` now begins to distinguish a small set of planning profiles so that not every task is forced into the same orchestration shape.

## Profiles

### `direct_review`
Use when the task is simple enough that dedicated research is not justified.

Default shape:
- execution
- review

### `research_execute_review`
Use when the task has meaningful acceptance criteria, constraints, or task types that usually benefit from context gathering.

Default shape:
- research
- execution
- review

### `research_execute_review_strict`
Use when the task is high-priority or belongs to stricter task families such as:
- `automation`
- `framework_design`

Default shape:
- research
- execution
- review with stricter review objective

## Current selection signals

The current implementation uses simple task-level signals:
- `task_type`
- `priority`
- presence of `acceptance`
- presence of `constraints`

This is intentionally lightweight.
The goal is to improve orchestration decisions without overcomplicating the framework.

## Why this matters

Before planning profiles, the framework mostly emitted the same plan shape for every task.
That made the framework easy to understand, but it also meant:
- small tasks could be over-orchestrated,
- task differences were under-modeled,
- review intensity could not scale with task strictness.

Planning profiles are the first step toward smarter orchestration while keeping the framework lightweight.
