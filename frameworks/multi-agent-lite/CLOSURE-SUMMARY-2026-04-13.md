# MULTI-AGENT-LITE CLOSURE SUMMARY

Date: 2026-04-13
Scope: `lulis-skill/frameworks/multi-agent-lite`
Focus: terminal-state closure + observability closure

---

## 1. What was actually broken

The staged collaboration path was producing a logically completed review result, but not a truly closed task state.

Concrete symptom:
- review returned `approved`
- review packet exposed `next_action = DONE`
- task-level result packet already looked delivered
- but task `status` remained at `REVIEW`
- outer framework therefore normalized the run as `in_progress`

This meant the framework had a **false live state**:
- semantically done
- structurally not done

That was the real reason the framework could not be treated as closed-loop yet.

---

## 2. What was added in this round

### 2.1 Task-level orchestrator trace

`core/orchestrator.py` was strengthened with a task-scoped trace surface:
- per-task event trace file under `runtime/orchestrator/traces/`
- registry rows under `runtime/orchestrator/registry.jsonl`
- snapshot payloads attached to each event

Covered events now include:
- `task_created`
- `state_changed`
- `plan_built`
- `task_dispatched`
- `execution_completed`
- `review_completed`

This closes a real observability gap:
- the framework no longer only stores task JSON state
- it now exposes a replayable collaboration timeline

### 2.2 Validation for orchestrator trace

Added:
- `validate_orchestrator_trace.py`

This validator confirms:
- trace file materializes
- expected events exist
- snapshots are attached
- final snapshot matches final task status
- orchestrator registry points back to the trace artifact

### 2.3 README capability update

`README.md` now explicitly states that the framework supports:
- task-level orchestrator trace artifacts
- registry rows for collaboration observability

---

## 3. The core bug fix

The real closure fix landed in:
- `core/review_state.py`

Before:
- `apply_review(...)` only wrote review objects back onto the task
- it did not convert review outcome into real task status progression

After:
- `approved` -> `DONE`
- `BLOCKED` / blocked sendback target -> `BLOCKED`
- manager replan -> `PLAN`
- execution rerun -> `EXECUTING`
- explicit ready -> `READY`
- explicit failed -> `FAILED`
- rerun cases increment `sendback_count` and set `rerun_execution_only` consistently

This is the real closure point of the round.

The framework now aligns three layers:
1. review decision
2. task status
3. outer normalized status

---

## 4. Validation result after the fix

All critical validations now pass:

1. `python3 validate_outer_framework.py`
2. `python3 validate_orchestrator_trace.py`
3. `python3 validate_coding_executor.py`

Most important outcome:
- staged approved path now resolves to:
  - `final_status = DONE`
  - `normalized_status = completed`

That removes the previous false-active state.

---

## 5. Why this round counts as real closure

This round did **not** just add another helper or another shell object.
It closed two concrete gaps that blocked the framework from being considered a tighter collaboration kernel:

1. **Observability gap closed**
   - there is now a task-level collaboration trace

2. **Terminal-state gap closed**
   - review outcomes now drive real task terminal/next states
   - outer status convergence is now structurally correct

That is a real system-quality improvement, not cosmetic expansion.

---

## 6. What is still intentionally not claimed

This round does **not** mean:
- production-hard autonomous runtime
- full session/runtime governance parity with a larger ecosystem
- complete persistence / replay / budget / permission stack
- final architecture maturity

Current honest claim:
- `multi-agent-lite` is now materially more closed-loop as a **bounded staged collaboration kernel**
- task lifecycle, rerun/sendback path, coding-lane feedback, outer convergence, and trace observability are now better aligned

---

## 7. Practical single-sentence summary

> `multi-agent-lite` now closes the staged approved path all the way through review -> task status -> outer normalized status, and it emits a task-level collaboration trace that makes the inner loop observable instead of opaque.
