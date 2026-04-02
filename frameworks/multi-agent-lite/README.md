# multi-agent-lite

A lightweight staged orchestration framework for OpenClaw.

## What it is

A four-role collaboration path built around:
- manager
- research
- execution
- reviewer

Core flow:

`create task -> plan -> dispatch -> execute -> review -> done / send back`

## Current stable value

Treat this as `v0.1` with real prototype value.

What is already materially working:
- staged planning / dispatch / execution / review
- OpenClaw executor integration
- planning-profile selection instead of one fixed plan shape
- task-type-aware expectations
- task-level delivery synthesis before review
- reviewer checks that lean on delivery signals, not only process completion
- local materializing mock fallback when external executor is unavailable

## Current stronger execution/review layer

The framework now also supports a stronger worker-to-reviewer contract:
- execution roles are expected to follow a worker-level loop (`understand -> act -> observe -> report -> stop/escalate`)
- executor output can carry structured acceptance checks
- executor output can state completion basis explicitly
- executor output can declare `needs_input` instead of hiding blockers
- review can downgrade optimistic acceptance detail when upstream execution has already failed

This is the main current direction of improvement: better delivery-quality control without replacing the core orchestrator.

## Boundaries

This framework is for orchestration discipline, not business truth.
Keep business rules, project mappings, templates, and domain validation outside the orchestration layer.

It is still not a production-hardened autonomous platform.
Executor quality, schema maturity, and runtime behavior still need continued tightening.

## Runtime vs validation vs mock

- **runtime path**: the actual staged orchestration and executor-backed flow
- **validation path**: `validate_delivery.py` and related scenario checks used to verify behavior
- **mock path**: local fallback / materializing behavior used when a real executor is unavailable

These layers should stay aligned, but they are not the same thing.
Do not let mock-specific convenience logic silently redefine runtime truth.

Practical interpretation:
- if a rule changes review decisions for real work, treat it as runtime-sensitive
- if a rule exists mainly to make deterministic local checks easier, keep it in validation/mock support
- if uncertain, document the boundary explicitly before promoting the behavior

## Validation

Quick checks:
- `python3 -m compileall frameworks/multi-agent-lite`
- `python3 frameworks/multi-agent-lite/main.py`
- `python3 frameworks/multi-agent-lite/validate_delivery.py`

`validate_delivery.py` is the more useful prototype check because it exercises:
- baseline delivery
- deliverable-required materialization
- failure-path send-back
- output-shape scenarios such as choice answering and path lookup

## Notes

This folder holds the framework implementation.
The triggerable skill lives in `../../skills/multi-agent-lite/`.
Project-facing usage guidance belongs in the skill references, not in this README.
