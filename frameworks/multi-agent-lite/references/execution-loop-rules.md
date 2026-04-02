# Execution loop rules

## Purpose

Strengthen the execution role without redesigning the framework.

`multi-agent-lite` already has staged orchestration, delivery synthesis, and review. This note defines the **minimum execution-loop discipline** that each execution role should follow before claiming a usable result.

This is the main absorbable lesson from `Claude Code from Scratch`: not a new orchestration framework, but a clearer worker-level loop.

## Minimum execution loop

Execution roles should implicitly follow:

1. **understand objective**
2. **check scope / constraints / acceptance**
3. **produce result or explicit blocker**
4. **return structured evidence**
5. **decide whether the task is actually in a deliverable state**

Do not skip from "I tried" to "done".

## Required behavior

### 1. Echo the task correctly

Before acting, the execution role should align to:
- task goal
- subtask objective
- acceptance items
- constraints
- required output shape

If these are materially unclear, prefer an explicit blocker over a vague draft.

### 2. Prefer deliverable signals over process narration

Execution should prioritize outputs that can be reviewed:
- concrete changes
- concrete artifacts
- direct answer form when task shape requires it
- concise summary of what was actually produced

Avoid long method narration unless it materially changes the review outcome.

### 3. Report blockers explicitly

If the role cannot produce a real deliverable, it should say so through:
- `unknowns`
- `needs_input`
- `risks`
- `next_suggestion`

Do not hide a blocker behind a generic summary.

### 4. Claim completion only with a basis

A result should only imply "ready for review" when at least one of these is true:
- meaningful changes were produced
- artifact(s) were produced
- a direct answer matching the required output shape was produced
- acceptance evidence can be pointed to directly

If none of those are true, the result should lean toward semantic failure / changes requested rather than optimistic completion.

### 5. Keep the return envelope compact

Execution output should be concise and structured.

Prefer:
- short `summary`
- bounded `raw_excerpt`
- task-relevant `changes`
- task-relevant `artifacts`
- explicit `acceptance_checks`

Avoid returning long free-form transcripts into task state.

## Contract handoff

Do not treat this file as the field-level contract source.

Field semantics and stability tiers belong in:
- `executor-contract.md`
- `schemas/result.schema.json`

This file only defines worker behavior expectations.

## Context discipline

Execution roles should treat context as layered:
- task state is for durable task signals
- runtime logs are for detailed process traces
- review should consume summaries and evidence first

If output is verbose, compress before returning it into task state.

## Non-goal

This note does **not** replace the orchestrator.
It only strengthens the execution role so the existing framework becomes more reliable.
