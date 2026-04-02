# Executor contract

## Purpose

Define the contract between the orchestration layer and the concrete executor implementation.

The executor must return a normalized result envelope so review and reporting can classify failures instead of guessing.

## Required envelope

```json
{
  "summary": "...",
  "changes": [],
  "artifacts": [],
  "risks": [],
  "unknowns": [],
  "next_suggestion": "...",
  "transport_error": false,
  "protocol_error": false,
  "semantic_error": false,
  "raw_excerpt": "..."
}
```

## Recommended extension fields

These are not all mandatory yet, but the framework should gradually prefer them because they make review less guess-based and more evidence-based.

### Recommended-now

```json
{
  "objective_echo": "what the executor believes the subtask is asking for",
  "acceptance_checks": [
    {"item": "...", "status": "pass|partial|fail|unknown", "evidence": "..."}
  ],
  "needs_input": ["..."],
  "completion_basis": ["artifact produced", "direct answer returned"]
}
```

### Secondary / still-soft

```json
{
  "assumptions": ["..."]
}
```

Interpretation:
- `objective_echo` reduces task-drift risk.
- `acceptance_checks` helps reviewer consume explicit checkpoint evidence.
- `needs_input` distinguishes a true blocker from a weak execution attempt.
- `completion_basis` explains why the executor believes the task is review-ready.
- `assumptions` is useful, but it is still softer than the fields above and should not be over-weighted in review.

## Error classes

### transport_error

Use when the executor could not reliably complete the call.

Examples:
- CLI invocation failed
- timeout
- process crash
- runtime unavailable

### protocol_error

Use when transport succeeded but the output did not satisfy the executor protocol.

Examples:
- non-JSON output
- malformed JSON
- missing required top-level shape after normalization

### semantic_error

Use when the payload is parseable but not meaningfully valid for the requested task.

Examples:
- empty or placeholder content
- required fields present but no meaningful result
- content does not address the requested objective

## Notes

- At most one of the three error booleans should normally be `true` for the primary failure cause.
- `raw_excerpt` should contain a short trimmed diagnostic excerpt when available.
- Review logic should consume these flags directly instead of inferring failure type from free text.
- Fields listed as `recommended-now` should be treated as the preferred contract for executor implementations and prompts, even if they are not yet hard-required by schema validation.
- In strict-review task types, repeated absence of `recommended-now` fields may justify send-back / `changes_requested` even without a transport/protocol/semantic hard failure.
- Fields listed as `soft_optional` should not quietly become review-critical without an explicit contract/schema promotion.
