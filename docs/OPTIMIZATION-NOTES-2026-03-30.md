# Optimization notes — 2026-03-30

This note captures the current structural assessment of `multi-agent-lite` and the most valuable next-step improvements.

## What is already solid

### 1. State machine discipline
The framework already has a clean task lifecycle:
- `NEW`
- `PLAN`
- `READY`
- `EXECUTING`
- `REVIEW`
- `DONE`
- `BLOCKED`
- `FAILED`
- `CANCELLED`

This is one of the stronger parts of the framework.
The status model is clearer than the current planning intelligence.

### 2. Role-to-model split exists
The repo already encodes a strong core idea:
- manager,
- research,
- execution,
- reviewer
should not all default to the same model.

This is the right direction for a multi-model environment.

### 3. Robustness improved in recent commit
The latest commit materially improved:
- stdout / stderr decoding tolerance,
- JSON extraction tolerance,
- executor / orchestrator fallback behavior.

These are practical upgrades, not cosmetic ones.

## What is still shallow

### 1. Planner is mostly static
The current planner always tends toward the same shape:
- research,
- execution,
- review.

That is acceptable for a prototype but not enough for stronger task routing.

### 2. Router is configuration-backed, not intelligence-backed
`models.json` provides role mappings, but the router still behaves like a static lookup table.
It does not yet decide based on:
- task size,
- ambiguity,
- risk,
- deliverable type,
- cost sensitivity.

### 3. Reviewer is still framework-centric
Current review logic mainly checks:
- task completion,
- assigned model presence,
- parse errors,
- executor errors.

This means the current reviewer is closer to a process-integrity checker than a deliverable-quality gate.

## High-value next steps

### Priority 1 — route tasks by complexity and risk
The framework should decide more explicitly between:
- direct / minimal orchestration,
- manager + execution + reviewer,
- manager + research + execution + reviewer.

Without this, even a multi-model environment will be underused or over-orchestrated.

### Priority 2 — strengthen reviewer standards
Reviewer logic should evolve from checking execution hygiene to checking delivery quality:
- goal coverage,
- acceptance fit,
- artifact usefulness,
- unresolved risks,
- verification path.

### Priority 3 — make task_type matter more
`task_type` should influence:
- plan shape,
- expected artifacts,
- review criteria,
- fallback strategy.

## Recommended interpretation

At the current stage, `multi-agent-lite` is best understood as:
- a usable multi-model orchestration skeleton,
- a promising internal production chain,
- not yet a deeply adaptive planner.

That is not a criticism.
It is a more accurate maturity label.
