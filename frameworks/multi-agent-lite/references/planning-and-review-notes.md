# Planning and review notes

## Current single source of truth

Planning profile selection lives in `core/planner.py`.
Task-type execution expectations live in `core/task_expectations.py`.
Task-level delivery assembly lives in `core/orchestrator.py`.
Review completion decisions live in `core/review_engine.py`.

When changing the framework, keep these four surfaces aligned.

## Current planning profiles

- `direct_review`
  - use for lightweight tasks
  - skip research
  - execute once, then review

- `research_execute_review`
  - use when acceptance items or constraints materially affect the work
  - gather context before execution
  - review against acceptance after execution

- `research_execute_review_strict`
  - use for stricter task types or higher-priority work
  - gather context
  - ask execution for a delivery-ready candidate
  - review with delivery readiness and unresolved risks in scope

## Current review interpretation

A task should not be considered done only because subtasks ran.
The framework should prefer task-level evidence:
- delivery summary
- deliverables / artifacts
- acceptance evidence
- explicit residual risks

If those are missing, prefer send-back over optimistic completion.

Also keep this distinction explicit:
- acceptance evidence pass means the task appears materially addressed
- executor contract quality pass means the execution result exposed enough structured review signals

These are related but not identical.
For strict-review task types, weak contract quality may still justify send-back even when acceptance evidence looks superficially positive.

## Reference split

Use this file for planning / review SSOT only.

- execution role discipline lives in `execution-loop-rules.md`
- result-envelope field semantics live in `executor-contract.md`
- runtime vs validation vs mock boundary rules live in `runtime-validate-mock-boundaries.md`
