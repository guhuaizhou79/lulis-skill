# MULTI-AGENT-LITE AUDIT FOLLOW-UP SUMMARY

Date: 2026-04-13
Scope: `lulis-skill/frameworks/multi-agent-lite`
Focus: post-closure structural audit and convergence fixes

---

## 1. Why this audit was needed

After the terminal-state closure fix, the framework was already materially healthier.
But that did not guarantee there were no second-order consistency bugs.

The audit therefore focused on:
- state transition consistency
- rerun / sendback truthfulness
- outer / raw_task / result-packet convergence
- whether coding tasks could still be silently misclassified

---

## 2. Real bug found and fixed

### 2.1 Coding task could bypass coding lane when repo_path was missing

Previously, outer only entered the coding lane when both were true:
- task is classified as coding
- `repo_path` is non-empty

That created a bad fallback:
- a coding task without repo context could skip coding-lane judgment
- then drift into staged success handling
- producing a potential false-success result

This has now been fixed.

New rule:
- if it is a coding task, it must go through coding-lane handling
- missing repo context must surface as blocked/failing semantics, not silent success fallback

This closes an important task-family boundary hole.

---

## 3. Result convergence fixes

### 3.1 Outer packet convergence was too weak for coding outcomes

Once coding-lane routing was enforced, another issue became visible:
- outer `final_status` could be `BLOCKED` or `PLAN`
- but `task_result_packet` still retained inner staged success residue

That meant the framework could still expose dual truths:
- top-level status says blocked/replan
- result packet still sounds delivered/successful

This has been fixed by strengthening outer convergence.

New behavior:
- blocked/replan coding outcomes now overwrite staged-success residue
- success coding outcomes now also converge into a coding-aware final packet path
- outer now emits `coding_result_packet` and aligns top-level `task_result_packet` to the same truth family

---

## 4. Deeper root cause fixed in coding executor contract

### 4.1 Executor status and review verdict could disagree

During audit, a lower-level inconsistency surfaced:
- executor `status` could still be `success`
- while `review_packet.verdict` was already `blocked`

That means the executor contract itself still allowed split truth.

This has now been fixed in `coding_executor_contract.py`.

New rule:
- executor result status now respects review verdict / validation-derived review outcome
- `blocked` verdict -> executor status `blocked`
- `needs_replan` verdict -> executor status `failed`
- accepted path remains `success`

This is more correct than trying to patch everything from outer only.

---

## 5. Validation update

### 5.1 Old coding success case was no longer a real success case

The previous `validate_outer_framework.py` success coding case had gone stale.
It did not represent a real coding-success setup under the stricter corrected semantics.

Instead of weakening the framework to satisfy an outdated test, the validator was updated to:
- use a real repo-backed coding success case
- preserve blocked / failing coding validation cases as separate explicit paths

This means the validation suite now matches the corrected architectural truth.

---

## 6. Validation outcome

After the audit fixes, all key validations pass again:

1. `python3 validate_outer_framework.py`
2. `python3 validate_orchestrator_trace.py`
3. `python3 validate_coding_executor.py`

---

## 7. Honest remaining note

One non-blocking information-quality limitation still exists:
- `coding_result_packet.repo_context.repo_context.repo_path` currently reflects payload-derived shaping rather than the richer executor-observed repo scan surface

This does **not** break status truth or routing correctness.
It is a future quality improvement, not a blocker.

---

## 8. Net result of this audit round

This round moved the framework from:
- “terminal state is closed”

to:
- “task family boundaries are stricter”
- “coding lane cannot silently fall back to false success”
- “outer and packet convergence are more single-truth”
- “executor status and review verdict are aligned”
- “validation suite matches corrected semantics”

---

## 9. One-line summary

> The audit round closed a hidden coding-task boundary hole, strengthened outer result convergence, aligned executor status with review verdict, and updated validation so the framework’s tests now reflect the corrected single-truth behavior.
