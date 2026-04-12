# MULTI-AGENT-LITE STAGE 2 SUMMARY

Date: 2026-04-12
Scope: `lulis-skill/frameworks/multi-agent-lite`
Stage focus: from outer-shell expansion to executor-first collaboration closure

---

## 1. Stage intent

Stage 2 was originally drifting toward continued outer-framework expansion:
- more governance objects
- more sendback wrappers
- more rerun policy surfaces
- more outer-side orchestration semantics

After comparing the current direction with the reference ecosystem (`claude-code-sourcemap`), the conclusion was:

> the real gap was not that outer lacked one more governance object.
> the real gap was that the coding side was still too thin.

So the stage was deliberately re-centered around **executor-first strengthening**.

This changed the question from:
- "what else should outer own?"

to:
- "what should executor know and emit so outer can stay smaller and still make better rerun decisions?"

---

## 2. Boundary decision

The most important decision of Stage 2 was to keep the role boundary strict:

- **outer** = governance / control / final rerun authority
- **coding executor** = bounded coding execution with repo-aware and validation-aware feedback

What was explicitly avoided:
- turning outer into a second total controller
- making executor own memory/docs/state authority
- copying the reference ecosystem's full size or shape
- introducing heavy parser / AST / new dependencies just to look more complete

The stage goal became:

> make executor produce more structured code-aware feedback,
> then let outer consume that feedback instead of guessing.

---

## 3. What was added on the executor side

### 3.1 Repo-aware context scan

The coding executor was extended so it no longer operates as a near-blind text editor.

Added surfaces include:
- `manifest_files`
- `entrypoint_hints`
- `source_dirs`
- `discovered_code_files`
- `language_hint`

This gives the executor a lightweight repo map without requiring heavyweight indexing.

### 3.2 Symbol-aware narrowing

A lightweight symbol extraction and ranking path was added.

Added surfaces include:
- symbol extraction from source text
- `repo_scan.symbol_index`
- goal-aware ranking
- narrowed active targets

Important constraint:
- this is intentionally lightweight text/regex-based narrowing
- not AST-first parsing
- not dependency-driven code intelligence

This was enough for the current stage because the main need was **better retry focus**, not full semantic tooling.

### 3.3 Structured validation surfaces

Validation was upgraded from generic pass/fail strings into explicit surfaces.

Added surfaces include:
- `syntax`
- `import`
- `unit`
- `project_command`

Executor output now carries:
- `validation_records`

This matters because rerun decisions should depend on **what kind of validation failed**, not only that something failed.

### 3.4 Validation policy mapping

The executor contract now derives a policy layer from validation outcomes.

Added logic:
- `_derive_validation_policy(...)`

Produced structure:
- `validation_policy.failed_surfaces`
- `validation_policy.blocked_surfaces`
- `validation_policy.verdict_hint`
- `validation_policy.manager_action_hint`
- `validation_policy.change_disposition_hint`

This gives outer a cleaner interface for interpreting failures.

### 3.5 Retry narrowing hints

The executor contract now also emits explicit narrowing suggestions for the next run.

Added logic:
- `_derive_retry_narrowing_hints(...)`

Produced structure:
- `scope_level`
- `target_files`
- `target_symbols`
- `validation_focus`
- `suggested_actions`

This is the key structural addition that made the stage feel complete.

Instead of outer deriving all retry scope indirectly, executor can now say:
- where to narrow
- how far to narrow
- what validation surface still matters

---

## 4. What was added on the outer side

Stage 2 did not stop at richer executor output.
The important follow-through was to make outer actually consume it.

### 4.1 Formal sendback / rerun path already in place

Before the final shift, outer already had:
- `manager_sendback_packet`
- `sendback_history`
- `sendback_count`
- `rerun_gate`
- `rerun_request`
- `rerun_dispatch`
- `change_disposition_policy`

These were useful, but there was still a risk:
- outer could keep becoming smarter by accreting more heuristics of its own
- instead of consuming structured executor-side feedback

### 4.2 Next payload builder now consumes executor feedback

This was the final integration step.

`build_next_executor_payload(...)` was updated so outer now prefers executor-produced:
- `validation_policy`
- `retry_narrowing_hints.target_files`
- `retry_narrowing_hints.target_symbols`
- `retry_narrowing_hints.validation_focus`

The next payload now carries:
- `target_symbols`
- `validation_focus`
- `executor_feedback`
- `builder_meta.used_executor_narrowing_hints`

This means outer is no longer mainly inferring retry shape from its own wrappers.
It is consuming structured downstream feedback and preserving role separation.

---

## 5. Why this stage is now considered closed-loop

By the end of Stage 2, the collaboration loop became materially tighter:

1. executor reads repo context
2. executor narrows file/symbol focus
3. executor runs validation and records validation surfaces
4. executor emits review + policy + narrowing hints
5. outer consumes those hints
6. outer decides rerun / block / escalate / narrower next payload

That is the minimum useful closure that was missing earlier.

Before this stage, outer had growing control objects but executor-side signal quality was still weak.
After this stage, outer has better decisions **without needing to become bigger in the wrong way**.

That is why this stage can be treated as a real closure point rather than just another milestone.

---

## 6. What was intentionally not done

To avoid false completeness, several things were explicitly left out.

### 6.1 No heavy AST / parser stack

Reason:
- current value did not justify dependency cost
- lightweight symbol-aware narrowing already solved the immediate need

### 6.2 No outer-side expansion into a second controller

Reason:
- would blur role boundaries
- would reproduce the wrong lesson from the reference ecosystem
- would increase governance surface faster than execution quality

### 6.3 No executor ownership of memory/docs/state

Reason:
- final authority still belongs to outer or higher layers
- coding execution should remain bounded

### 6.4 No copy-style replication of the reference repo

Reason:
- the reference was used for pattern learning
- not as a template to mirror one-to-one

---

## 7. Validation status

This stage was not only implemented but repeatedly validated.

Validated paths include:
- coding executor evolution via `validate_coding_executor.py`
- outer integration and rerun shaping via `validate_outer_framework.py`

The outer validation now confirms that:
- `next_executor_payload` is emitted for failing coding runs
- outer includes executor feedback in the next payload
- `validation_focus` is preserved
- `builder_meta.used_executor_narrowing_hints` becomes `true` when executor narrowing is actually used

This matters because the stage claim is not just architectural intent.
It is reflected in validation behavior.

---

## 8. Resulting architectural shape

After Stage 2, the architecture is better described as:

- **outer**: route selection, governance, rerun authority, escalation, final packaging
- **coding executor**: repo-aware editing lane, validation-aware execution lane, narrowing-aware retry signal producer

The key improvement is not “more layers”.
The key improvement is:

> better signal quality from executor to outer,
> so outer can stay authoritative without staying blind.

---

## 9. Recommended next move

Do not keep extending this stage just because more structure could still be added.

The recommended next move is one of two:

1. map this collaboration pattern into the real business automation framework
2. open a new stage only if a new gap is concrete and verified

What should not happen next:
- arbitrary outer expansion for symmetry
- dependency-heavy parsing work without a verified need
- treating “can add more” as “should add more”

---

## 10. Short conclusion

Stage 2 started by looking like outer-framework strengthening.
It ended in a better place:

- executor became more code-aware
- validation became more structured
- retry narrowing became explicit
- outer learned to consume executor feedback instead of guessing
- boundary discipline stayed intact

That is why Stage 2 should be remembered as:

> the stage where `multi-agent-lite` stopped growing mainly by outer wrappers,
> and started closing the loop between code execution feedback and outer rerun control.
