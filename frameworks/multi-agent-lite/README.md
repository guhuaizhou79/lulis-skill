# multi-agent-lite

A lightweight multi-agent collaboration framework for OpenClaw.

## What it is

A staged orchestration path built around:
- manager
- research
- execution
- reviewer

## Current flow

`create task -> plan -> dispatch -> execute -> review -> done / send back`

## Current maturity

Treat this as `v0.1`:
- main chain works,
- OpenClaw executor is connected,
- executor robustness has improved with output decoding, JSON extraction tolerance, and fallback handling,
- planning now follows explicit profile selection instead of a single fixed path,
- reviewer now checks task-level delivery signals instead of only process completion,
- task-level synthesis now aggregates delivery changes, evidence, and deliverable candidates before review,
- there is still a gap between a usable internal pipeline and a fully production-hardened autonomous platform.

## Recommended interpretation

Use this framework as a disciplined internal multi-model production chain.
Its strongest current value is a runtime-first staged workflow that can degrade to a local materializing mock path when the external executor is unavailable.

Its strongest value is staged quality control:
- planning,
- research,
- execution,
- review.

The framework now distinguishes lightweight planning profiles:
- `direct_review`
- `research_execute_review`
- `research_execute_review_strict`

These profiles are selected from task type, priority, acceptance items, and constraints, so plan shape is now more explicit and closer to SSOT.

The framework also now encodes simple task-type expectations and stronger reviewer checks, so it is moving from pure process control toward basic delivery-quality control.

This is still intentionally simple, but it is a better direction than forcing the same plan shape for every task.

Do not confuse the orchestration layer with business truth.
Business rules, mappings, templates, and project-specific validation should remain separate.

## Validation

Quick checks:
- `python3 -m compileall frameworks/multi-agent-lite`
- `python3 frameworks/multi-agent-lite/main.py`
- `python3 frameworks/multi-agent-lite/validate_delivery.py`

`validate_delivery.py` is the more useful prototype check because it exercises baseline delivery, deliverable-required materialization, failure-path send-back, and output-shape scenarios such as choice answering and path lookup.

## Notes

This folder holds the framework implementation.
The triggerable skill lives in `../../skills/multi-agent-lite/`.
For project-facing operating guidance, also see `../../skills/multi-agent-lite/references/project-usage-guide.md`, `../../docs/MULTI-MODEL-ADOPTION.md`, `../../docs/OPTIMIZATION-NOTES-2026-03-30.md`, and `../../docs/NEXT-IMPLEMENTATION-CUTS.md`.
