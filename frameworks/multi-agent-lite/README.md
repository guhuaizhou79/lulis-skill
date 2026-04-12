# multi-agent-lite

A lightweight staged orchestration framework for OpenClaw.

## What it is

`multi-agent-lite` is a **bounded staged collaboration kernel**.

It is good at:
- planning -> execution -> review task structure
- lightweight role separation
- review-driven sendback
- selective execution rerun
- compact task-level result packaging

It is **not** intended to be:
- a global controller for all work
- a memory / writeback governor
- a replacement for the outer framework
- the default path for every task

The correct integration model is:

> outer framework decides whether to use direct / light / staged path, and `multi-agent-lite` only owns the staged inner loop.

---

## Current runtime capabilities

As of the current first-cut runtime, `multi-agent-lite` already supports:

- structured `handoff` attached during dispatch
- `task_result_packet` synthesis at task level
- `review_verdict` merge back into task-level result packet
- `gap_groups` + review routing hints
- `sendback_count` and `degrade_history`
- `orchestration_mode` downgrade (`full -> compact -> minimal`)
- selective `review -> execution` rerun path
- stale / active evidence split
- `artifact_lifecycle` tracking across reruns
- unified validation entrypoint
- task-level orchestrator trace artifacts and registry rows for collaboration observability

---

## Outer adapter

A first-cut outer adapter shim now exists at:

- `frameworks/multi-agent-lite/outer_adapter.py`

It provides:
- `choose_route(payload)`
- `run_multi_agent_lite(root, payload)`
- `build_outer_result(task)`
- `run_adapter(root, payload)`

### Recommended outer routing model

Use three routes at the outer layer:

- `direct`
- `light_role_check`
- `multi_agent_lite`

#### Prefer `direct`
When the task is:
- one-turn answerable
- lightweight judgment / explanation
- simple fact / choice / path lookup

#### Prefer `light_role_check`
When the task needs:
- a little structure
- a lightweight self-check
- but not a full plan/execute/review loop

#### Prefer `multi_agent_lite`
When the task needs:
- explicit staged collaboration
- planning / execution / review separation
- review-driven rerun or sendback discipline
- a compact but auditable task-level result

---

## Outer framework skeleton

A first-cut outer framework shell now also exists at:

- `frameworks/multi-agent-lite/outer_framework.py`

It currently provides:
- task shape classification
- route selection orchestration
- direct / light / staged dispatch shell
- unified outer result convergence
- route explanation
- normalized outer status
- advisory writeback policy stub

### Normalized outer status

The outer shell exposes a simplified status layer so upper callers do not need to interpret every inner runtime status directly.

Current normalized statuses include:
- `completed`
- `needs_execution_rerun`
- `needs_replan`
- `blocked`
- `failed`
- `in_progress`

### Writeback policy stub

The outer shell also exposes:
- `writeback_policy`

This is intentionally advisory-only.
It may recommend whether a result is worth:
- summary writeback
- memory writeback
- state writeback

But it must not directly mutate global memory/docs/state surfaces by itself.

### Coding rerun feedback boundary

For coding tasks, the outer framework now consumes executor-produced rerun signals instead of inventing the next retry scope by itself.

Current executor -> outer feedback surface:
- `validation_policy`
- `retry_narrowing_hints.target_files`
- `retry_narrowing_hints.target_symbols`
- `retry_narrowing_hints.validation_focus`

Current outer behavior:
- keeps final rerun / sendback authority
- builds `next_executor_payload`
- prefers executor-provided narrowing hints over broad outer-side guessing
- carries the consumed feedback forward as `executor_feedback`

This keeps the boundary clean:
- **executor** says what failed, where to narrow, and which validation surface matters next
- **outer** decides whether to rerun, block, escalate, or hand back a narrower payload

The goal is not to make outer a second code-aware controller.
The goal is to let outer consume structured executor feedback without losing role separation.

---

## Validation

Primary validation entrypoint:

- `python3 frameworks/multi-agent-lite/validate_delivery.py`

Additional adapter validation:

- `python3 frameworks/multi-agent-lite/validate_outer_adapter.py`

Outer framework validation:

- `python3 frameworks/multi-agent-lite/validate_outer_framework.py`

Orchestrator trace validation:

- `python3 frameworks/multi-agent-lite/validate_orchestrator_trace.py`

Backward-compatible wrapper:

- `python3 frameworks/multi-agent-lite/validate_handoff_and_result_packet.py`

### What the unified validation covers

`validate_delivery.py` currently covers:
- baseline staged flow
- deliverable-required flow
- semantic failure -> rerun-ready routing
- strict review contract-gap routing
- handoff presence
- task_result_packet generation
- degrade history
- selective execution rerun
- stale evidence retention
- artifact lifecycle retention

---

## Integration boundary

The outer framework should consume these first:
- `task_result_packet`
- `final_status`
- `orchestration_mode`
- `degrade_history`
- `artifact_lifecycle`

Do **not** let `multi-agent-lite` directly decide global writeback.
It may emit:
- `writeback_recommendation`
- `writeback_hint`

But outer framework should remain the final authority for:
- memory writes
- docs writes
- state sync
- working-summary / current-state updates

---

## Repo map

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
