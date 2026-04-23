# Multi-Agent Collaboration Round 1 Implementation Plan

> **For Hermes:** Use `subagent-driven-development` to implement this plan task-by-task once the plan is approved for execution.

**Goal:** Upgrade Hermes multi-agent collaboration from “can delegate” to “stable, observable, and handoff-friendly” without attempting a full orchestration rewrite.

**Architecture:** This round intentionally avoids large-scale adapter and scheduler redesign. It focuses on four bounded improvements: (1) remove process-global tool resolution state, (2) emit structured subagent progress events, (3) standardize child result payloads, and (4) persist delegation metadata into parent/session/trajectory/memory flows.

**Tech Stack:** Python 3.11, pytest, Hermes core agent runtime, gateway progress callbacks, session/trajectory plumbing.

---

## Scope and Non-Goals

### In scope
- Remove process-global `_last_resolved_tool_names` dependency
- Replace delegation progress string bias with structured event payloads
- Expand child result payload into a stable schema suitable for parent aggregation and later reviewer flows
- Attach delegation lineage/metadata to memory and trajectory surfaces
- Add regression tests around delegation concurrency and structured events

### Out of scope for round 1
- Full shared execution budget/governor redesign
- ExternalAgentAdapter abstraction
- OpenClaw worker-role formalization
- Planner→implementer→reviewer orchestration templates
- New user-facing CLI commands

---

## Current Evidence Baseline

Before implementation, these code facts should still be true and should be used as the starting point:

- `model_tools.py` writes process-global `_last_resolved_tool_names`
- `tools/delegate_tool.py` saves/restores tool state to work around global mutation
- `tools/delegate_tool.py` returns child summaries but not a richer artifact contract
- `tools/delegate_tool.py` sends progress primarily as text-oriented callback updates
- `tools/delegate_tool.py` already attaches `parent_session_id` when constructing child agents
- `agent/memory_provider.py` and `agent/memory_manager.py` already have delegation hook plumbing, but metadata is thin

---

## Phase 0 — Baseline Verification

### Task 0.1: Reconfirm current delegation behavior

**Objective:** Capture the current implementation assumptions before modifying shared runtime code.

**Files:**
- Inspect: `model_tools.py`
- Inspect: `tools/delegate_tool.py`
- Inspect: `run_agent.py`
- Inspect: `gateway/run.py`
- Inspect: `agent/memory_provider.py`
- Inspect: `agent/memory_manager.py`
- Inspect: `agent/trajectory.py`

**Step 1: Verify current global tool-state writes**

Search for `_last_resolved_tool_names` and note:
- write sites
- read sites
- save/restore logic in delegation code

**Step 2: Verify current subagent progress behavior**

Inspect the callback path and confirm whether the gateway is consuming structured metadata or mostly text.

**Step 3: Run current delegation-focused tests**

Run:
```bash
source venv/bin/activate
python -m pytest tests/tools/test_delegate.py -q
python -m pytest tests/tools/test_delegate_toolset_scope.py -q
python -m pytest tests/agent/test_subagent_progress.py -q
python -m pytest tests/run_agent/test_interrupt_propagation.py -q
python -m pytest tests/run_agent/test_real_interrupt_subagent.py -q
```

**Expected:** Current baseline passes before any edits.

---

## Phase 1 — Remove Process-Global Tool State (P0)

### Task 1.1: Enumerate all `_last_resolved_tool_names` dependencies

**Objective:** Find the full impact surface before replacing the global state.

**Files:**
- Inspect: `model_tools.py`
- Inspect: `tools/delegate_tool.py`
- Inspect: any additional matches from repo search

**Step 1: Search for all references**

Run a targeted search and list every read/write location.

**Step 2: Categorize each usage**

For each reference, classify it as one of:
- writer
- consumer
- workaround/restore logic
- debugging/logging only

**Step 3: Record migration target**

For each consumer, decide whether it should read:
- `AIAgent` instance state, or
- call-local resolved tool metadata

**Verification:** No hidden dependency remains unaccounted for.

---

### Task 1.2: Move resolved tool names to `AIAgent` instance state

**Objective:** Make resolved tool state local to the agent instance rather than the process.

**Files:**
- Modify: `run_agent.py`
- Modify: `model_tools.py`
- Possibly modify: callers that currently rely on global state side effects

**Step 1: Add instance field to `AIAgent`**

Introduce an instance-level field, for example:
```python
self._resolved_tool_names: list[str] = []
```

**Step 2: Update tool resolution flow**

Refactor the tool-definition pipeline so that resolved tool names are returned or attached explicitly to the current agent instance.

**Step 3: Remove global write side effect**

Delete the global mutation pattern in `model_tools.py` and replace it with explicit state flow.

**Verification:**
- No process-global resolved tool list remains authoritative
- An `AIAgent` instance can read its own resolved tool names without touching module globals

---

### Task 1.3: Remove delegation save/restore patches for global tool state

**Objective:** Delete workaround logic that only exists because tool state was global.

**Files:**
- Modify: `tools/delegate_tool.py`

**Step 1: Remove parent snapshot logic**

Delete logic that captures parent `_last_resolved_tool_names` before child creation.

**Step 2: Remove child restore logic**

Delete logic that restores tool names after child completion.

**Step 3: Keep behavior intact**

Ensure delegation still preserves correct child toolsets and parent tool context, now via explicit agent state.

**Verification:**
- No save/restore workaround remains for resolved tool names
- Delegation behavior still matches pre-change behavior from the user’s perspective

---

### Task 1.4: Add concurrency regression coverage for tool-state isolation

**Objective:** Prove that multiple children do not leak resolved tool state across each other or into the parent.

**Files:**
- Modify: `tests/tools/test_delegate.py`
- Possibly create: `tests/tools/test_delegate_concurrency.py`

**Step 1: Add parent+child isolation test**

Test that a parent agent retains its own resolved tool view after spawning a child with a narrower toolset.

**Step 2: Add sibling isolation test**

Test that two children with different toolsets do not overwrite each other’s resolved tool metadata.

**Step 3: Add repeated delegation test**

Spawn children sequentially and ensure the second does not inherit stale tool-state from the first.

**Verification:** Delegation concurrency tests pass reliably.

---

## Phase 2 — Structured Subagent Progress Events (P1)

### Task 2.1: Define a stable child event schema

**Objective:** Establish a structured event contract before changing runtime behavior.

**Files:**
- Modify: `tools/delegate_tool.py`
- Possibly document in: `website/docs/developer-guide/architecture.md` or a follow-up doc

**Step 1: Define initial event types**

Minimum event types:
- `subagent.started`
- `subagent.tool.started`
- `subagent.tool.completed`
- `subagent.progress`
- `subagent.completed`
- `subagent.failed`

**Step 2: Define minimum payload fields**

Minimum payload fields should include:
```python
{
    "task_index": 0,
    "child_session_id": "sess_xxx",
    "goal_preview": "inspect delegation flow",
    "tool": "read_file",
    "iteration": 2,
    "status": "running",
    "timestamp": "...",
}
```

**Step 3: Keep UI compatibility**

Decide that CLI/Gateway display strings will be derived from these events, not vice versa.

**Verification:** Event schema is small, explicit, and reusable.

---

### Task 2.2: Refactor child progress callback generation

**Objective:** Emit structured event payloads from delegation runtime.

**Files:**
- Modify: `tools/delegate_tool.py`

**Step 1: Update `_build_child_progress_callback()`**

Change the callback builder so it emits structured payloads instead of primarily free-form strings.

**Step 2: Include child identity metadata**

Ensure emitted events include:
- `task_index`
- `child_session_id`
- `goal_preview`
- event-specific fields such as `tool`, `status`, `iteration`

**Step 3: Preserve text rendering as a derived layer**

If callers still need text, derive it from the structured event object.

**Verification:** Delegation emits machine-readable child lifecycle events.

---

### Task 2.3: Teach gateway progress handlers to surface child lifecycle events

**Objective:** Make child execution visible outside the internal runtime.

**Files:**
- Modify: `gateway/run.py`
- Inspect: compatibility handling in any step-callback helpers/tests

**Step 1: Recognize child event types**

Update gateway progress handling to accept the new structured event names/types.

**Step 2: Render a minimal but useful view**

At minimum, surface:
- child started
- current tool started/completed
- child completed/failed
- elapsed time or status if available

**Step 3: Avoid breaking existing progress consumers**

Keep backward compatibility if older text-style callbacks still appear.

**Verification:** Gateway output no longer hides most subagent lifecycle information.

---

### Task 2.4: Add tests for structured progress propagation

**Objective:** Prevent regressions in CLI/gateway visibility.

**Files:**
- Modify: `tests/agent/test_subagent_progress.py`
- Modify: `tests/gateway/test_step_callback_compat.py`

**Step 1: Add event emission unit tests**

Assert that delegation emits structured child events with required fields.

**Step 2: Add gateway compatibility tests**

Assert that gateway handlers accept structured child events without breaking older callback paths.

**Step 3: Add completion/failure cases**

Test both successful and failing child events.

**Verification:** Child lifecycle events are test-covered end to end.

---

## Phase 3 — Structured Child Result Contract (P1)

### Task 3.1: Define the minimum result schema for delegated children

**Objective:** Standardize child outputs into a stable parent-consumable shape.

**Files:**
- Modify: `tools/delegate_tool.py`
- Possibly document in a developer guide follow-up

**Step 1: Define result contract**

Minimum shape:
```python
{
    "task_index": 0,
    "status": "completed",
    "summary": "...",
    "findings": [],
    "evidence": [],
    "files_touched": [],
    "commands_run": [],
    "tool_trace": [],
    "blockers": [],
    "confidence": None,
    "recommended_next_action": "",
    "api_calls": 0,
    "duration_seconds": 0.0,
    "tokens": {},
    "exit_reason": "",
}
```

**Step 2: Mark optional first-round fields**

Allow `findings`, `evidence`, `confidence`, and `recommended_next_action` to be empty/None initially.

**Step 3: Preserve backward compatibility**

Do not remove legacy fields that callers may already expect.

**Verification:** A single stable schema exists for all child outcomes.

---

### Task 3.2: Expand `_run_single_child()` result assembly

**Objective:** Make runtime output match the new schema without overcomplicating extraction.

**Files:**
- Modify: `tools/delegate_tool.py`

**Step 1: Preserve current fields**

Keep existing summary/status/api_calls/duration/tool_trace behavior.

**Step 2: Add empty/default structured fields**

Populate stable placeholders for:
- `findings`
- `evidence`
- `files_touched`
- `commands_run`
- `blockers`
- `recommended_next_action`
- `exit_reason`

**Step 3: Fill failure metadata**

When a child fails/interrupted/errors, ensure `status`, `blockers`, and `exit_reason` are explicit.

**Verification:** Every child result conforms to the same shape regardless of success/failure.

---

### Task 3.3: Improve child completion prompt guidance

**Objective:** Increase result quality without forcing fragile strict JSON output.

**Files:**
- Modify: `tools/delegate_tool.py` (child prompt/system prompt assembly)

**Step 1: Add semi-structured completion guidance**

Instruct children to finish with a concise shape covering:
- key findings
- strongest evidence
- blockers
- recommended next step

**Step 2: Avoid hard JSON-only requirements**

Round 1 should not force brittle JSON parsing in every child completion.

**Step 3: Let parent assemble the final structured object**

Use the child text as input, but let the parent own the final schema.

**Verification:** Child summaries become more consistently reviewable without causing new formatting failures.

---

### Task 3.4: Add child result schema regression tests

**Objective:** Ensure success/failure/interruption paths all produce consistent results.

**Files:**
- Modify: `tests/tools/test_delegate.py`

**Step 1: Add success-case assertion**

Assert that completed child results contain required fields.

**Step 2: Add failure-case assertion**

Assert that failed child results populate `status`, `blockers`, and `exit_reason`.

**Step 3: Add batch-case assertion**

Assert that all child results in batch mode share the same schema.

**Verification:** Parent code can depend on a stable child result contract.

---

## Phase 4 — Persist Delegation Metadata into Memory / Session / Trajectory (P1)

### Task 4.1: Expand delegation metadata passed to memory hooks

**Objective:** Make memory providers delegation-aware without re-reading child transcripts.

**Files:**
- Modify: `tools/delegate_tool.py`
- Modify: `agent/memory_provider.py`
- Modify: `agent/memory_manager.py`

**Step 1: Extend hook call payload**

Pass additional data into `on_delegation(...)`, such as:
- `status`
- `duration_seconds`
- `api_calls`
- `tool_trace`
- `blockers`
- `recommended_next_action`
- `task_index`

**Step 2: Preserve compatibility with existing providers**

Use kwargs/default handling so existing providers do not break.

**Step 3: Add tests or provider fakes**

Confirm memory providers can observe the richer metadata.

**Verification:** Memory surfaces delegation outcomes with richer context.

---

### Task 4.2: Add delegation lineage fields to trajectory/session events

**Objective:** Make parent-child execution chains reconstructable.

**Files:**
- Modify: `agent/trajectory.py`
- Modify: `run_agent.py`
- Inspect/modify if needed: `hermes_state.py`

**Step 1: Define lineage metadata**

Minimum lineage fields:
- `session_id`
- `parent_session_id`
- `delegate_depth`
- `task_index`
- `source`

**Step 2: Attach lineage to subagent-related events**

Make sure subagent runs write enough metadata for tree reconstruction.

**Step 3: Keep old consumers safe**

Add fields without removing existing event properties.

**Verification:** A delegation run can be reconstructed as a hierarchy rather than unrelated flat logs.

---

### Task 4.3: Write compact child outcome records into the parent session

**Objective:** Let parent sessions remain understandable even without opening each child transcript.

**Files:**
- Modify: `run_agent.py`
- Inspect/modify if needed: `hermes_state.py`

**Step 1: Create a delegation result event record**

Record a compact parent-visible result such as:
```python
{
    "type": "delegation_result",
    "task_index": 0,
    "child_session_id": "sess_xxx",
    "status": "completed",
    "summary": "...",
}
```

**Step 2: Include the most useful metadata**

If cheap to include, also store:
- `duration_seconds`
- `api_calls`
- `blockers`
- `recommended_next_action`

**Step 3: Ensure session-search friendliness**

Keep the record concise and text-searchable.

**Verification:** Parent session history can explain what each child accomplished.

---

## Phase 5 — Validation and Regression Closure

### Task 5.1: Run targeted delegation tests

**Objective:** Verify round-1 changes without immediately paying full-suite cost.

**Files:**
- Test: `tests/tools/test_delegate.py`
- Test: `tests/tools/test_delegate_toolset_scope.py`
- Test: `tests/agent/test_subagent_progress.py`
- Test: `tests/gateway/test_step_callback_compat.py`
- Test: `tests/run_agent/test_interrupt_propagation.py`
- Test: `tests/run_agent/test_real_interrupt_subagent.py`

**Run:**
```bash
source venv/bin/activate
python -m pytest tests/tools/test_delegate.py -q
python -m pytest tests/tools/test_delegate_toolset_scope.py -q
python -m pytest tests/agent/test_subagent_progress.py -q
python -m pytest tests/gateway/test_step_callback_compat.py -q
python -m pytest tests/run_agent/test_interrupt_propagation.py -q
python -m pytest tests/run_agent/test_real_interrupt_subagent.py -q
```

**Expected:** All pass.

---

### Task 5.2: Add realistic mixed-outcome regression scenarios

**Objective:** Verify behavior under the collaboration patterns this refactor is meant to improve.

**Files:**
- Modify/create delegation-related tests under `tests/tools/` and `tests/agent/`

**Scenarios:**
1. Parent with two children using different toolsets
2. One child succeeds while another fails
3. Structured progress reaches gateway handlers
4. Memory hook receives structured delegation metadata
5. Parent retains enough session context to understand child outcomes

**Verification:** Mixed real-world delegation behavior remains stable.

---

### Task 5.3: Run broader regression sweep

**Objective:** Confirm no collateral damage in adjacent runtime layers.

**Run:**
```bash
source venv/bin/activate
python -m pytest tests/tools/ -q
python -m pytest tests/agent/ -q
python -m pytest tests/gateway/ -q
```

If runtime/session changes are broader than expected, finish with:
```bash
source venv/bin/activate
python -m pytest tests/ -q
```

**Expected:** No regressions outside delegation-specific tests.

---

## Recommended Implementation Order

1. Phase 0 — baseline verification
2. Phase 1 — remove process-global tool state
3. Phase 2 — structured progress events
4. Phase 3 — structured child result schema
5. Phase 4 — memory/session/trajectory writeback
6. Phase 5 — regression closure

This ordering minimizes risk because:
- Phase 1 removes the most dangerous shared-state flaw first
- Phase 2 and 3 improve observability and handoff without large architectural churn
- Phase 4 builds persistence only after event/result shapes stabilize

---

## Suggested Ownership Split

### Good candidates for subagent implementation
- Test additions in `tests/tools/` and `tests/agent/`
- Structured result-schema expansion in `tools/delegate_tool.py`
- Gateway compatibility display updates once event schema is fixed

### Better kept under main-agent control
- `model_tools.py` global-state removal
- `run_agent.py` state plumbing
- session/trajectory lineage changes
- anything that could destabilize core runtime invariants

---

## Acceptance Criteria for Round 1

Round 1 is complete when all of the following are true:

1. `model_tools.py` no longer relies on process-global `_last_resolved_tool_names`
2. `tools/delegate_tool.py` no longer saves/restores global tool state during child execution
3. Delegation emits structured child lifecycle events
4. Gateway/CLI compatibility remains intact
5. Every child result conforms to a stable schema with explicit success/failure fields
6. Memory/session/trajectory surfaces include richer delegation metadata and lineage
7. Delegation-focused tests pass, followed by broader tools/agent/gateway regression coverage

---

## Round 2 Preview (Do Not Mix Into Round 1)

These are intentionally deferred until round 1 lands cleanly:
- shared execution/delegation budget
- unified concurrency governor
- `ExternalAgentAdapter`
- OpenClaw worker formalization
- planner→implementer→reviewer orchestration templates

Keeping them out of round 1 reduces scope creep and makes verification tractable.
