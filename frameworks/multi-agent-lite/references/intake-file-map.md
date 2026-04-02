# Repo intake file map

## Purpose

Define the first-pass intake boundary for moving the current working version toward a repo-ready form.

This file answers:
- what should be treated as core intake surface,
- what should be treated as support surface,
- what should stay out of first-pass intake until further cleanup.

## 1. Core intake surface

These files express real framework behavior or its closest SSOT and should be included in the first repo-ready intake set.

### Framework runtime / core
- `core/orchestrator.py`
- `core/planner.py`
- `core/execution_runner.py`
- `core/openclaw_executor.py`
- `core/review_engine.py`
- `core/task_expectations.py`
- `core/delivery_synthesizer.py`
- `core/acceptance_mapping.py`

### Validation / prototype checks
- `validate_delivery.py`
- `main.py`

### Schemas
- `schemas/result.schema.json`
- `schemas/review.schema.json`
- `schemas/task.schema.json`

### Primary framework docs
- `README.md`
- `references/executor-contract.md`
- `references/planning-and-review-notes.md`
- `references/runtime-validate-mock-boundaries.md`

### Skill-facing entry points
- `../../skills/multi-agent-lite/SKILL.md`
- `../../skills/multi-agent-lite/references/framework-status.md`
- `../../skills/multi-agent-lite/references/project-usage-guide.md`
- `../../skills/multi-agent-lite/references/repo-layout.md`

## 2. Support surface

These are useful, but not all of them are equally core to first-pass repo intake.

- `core/mock_executor.py`
- `references/execution-loop-rules.md`
- `configs/*.json`
- `roles/*.py`
- runtime placeholder directories / `.gitkeep`

Guidance:
- include if the repo should remain runnable / explainable end-to-end,
- but do not let support files become a substitute for runtime SSOT.

## 3. Keep out of first-pass intake unless cleaned

These should not drive first-pass intake decisions.

- workspace-top-level exploratory docs that duplicate framework truths
- ad-hoc temporary diff notes
- temporary comparison copies under `tmp/`
- any mock-only convenience logic that is not clearly marked as mock support

## 4. Practical rule

If a file changes real task execution, review decisions, result contract semantics, or validation expectations, it belongs near the core intake surface.

If a file mainly explains, scaffolds, or locally simulates behavior, it belongs in support unless proven otherwise.
