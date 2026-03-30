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
- there is still a gap between a usable internal pipeline and a fully production-hardened autonomous platform.

## Recommended interpretation

Use this framework as a disciplined internal multi-model production chain.
Its strongest value is staged quality control:
- planning,
- research,
- execution,
- review.

The framework now also begins to distinguish lightweight planning profiles:
- `direct_review`
- `research_execute_review`
- `research_execute_review_strict`

This is still intentionally simple, but it is a better direction than forcing the same plan shape for every task.

Do not confuse the orchestration layer with business truth.
Business rules, mappings, templates, and project-specific validation should remain separate.

## Notes

This folder holds the framework implementation.
The triggerable skill lives in `../../skills/multi-agent-lite/`.
For project-facing operating guidance, also see `../../skills/multi-agent-lite/references/project-usage-guide.md`, `../../docs/MULTI-MODEL-ADOPTION.md`, `../../docs/OPTIMIZATION-NOTES-2026-03-30.md`, and `../../docs/NEXT-IMPLEMENTATION-CUTS.md`.
