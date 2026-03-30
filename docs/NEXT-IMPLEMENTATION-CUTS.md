# Next implementation cuts

This document proposes the smallest high-value implementation cuts for improving `multi-agent-lite` without over-expanding the framework.

## Goal

Improve framework quality by strengthening the weakest control points first.

The point is not to add more moving parts.
The point is to make the current path smarter and more reliable.

## Cut 1 — planning profile selection

### Problem
The current planner mostly emits the same shape:
- research
- execution
- review

This causes two issues:
- small tasks can be over-orchestrated,
- different task types do not receive meaningfully different plans.

### Proposed minimum improvement
Introduce a lightweight planning profile decision before building subtasks.

Possible profiles:
- `direct_review`
- `research_execute_review`
- `research_execute_review_strict`

### Decision inputs
Use simple task-level signals such as:
- `task_type`
- number of acceptance criteria
- whether constraints are present
- whether the task is marked high priority

### Why this is the best first cut
It upgrades intelligence without forcing a redesign of the framework.

## Cut 2 — reviewer quality checks

### Problem
The current reviewer mainly checks execution hygiene:
- assigned model present,
- execution completed,
- no parse error,
- no executor error.

This is necessary but not sufficient.

### Proposed minimum improvement
Add a second review layer that checks deliverable quality signals such as:
- whether execution produced meaningful `changes`,
- whether known `risks` remain unresolved,
- whether acceptance criteria are at least referenced or addressed,
- whether the task produced any artifacts when artifacts are expected.

### Why this matters
A framework named around review should not stop at process completeness.

## Cut 3 — task-type expectations

### Problem
`task_type` currently affects execution role selection only in a limited way.

### Proposed minimum improvement
Define simple expectations per task type, for example:
- `code` → executable or patch-like output expected
- `framework_design` → structure / rationale / next-step clarity expected
- `automation` → workflow steps and fallback path expected
- `general` → concise deliverable with explicit risks expected

These expectations can then be used by both planner and reviewer.

## Suggested implementation order

1. planning profile selection
2. task-type expectations
3. reviewer quality checks

This order keeps the framework coherent:
- plan better,
- know what should exist,
- review against that expectation.

## Explicit non-goals for now

Do not add yet:
- deep recursive planning,
- parallel execution complexity,
- dynamic cost optimization,
- complex memory subsystems,
- large role catalogs.

Those would expand surface area too early.

## Recommendation

Treat these as the next realistic implementation cuts if the goal is to make `multi-agent-lite` meaningfully better while preserving its lightweight character.
