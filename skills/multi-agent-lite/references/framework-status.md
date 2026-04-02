# Framework status

## Current definition

`multi-agent-lite` is a lightweight staged orchestration framework for OpenClaw.

It currently supports:
- task creation
- planning
- role-based dispatch
- executor-backed execution
- review loop
- done / send-back flow

## Current role set

- manager
- research
- execution
- reviewer

## Stable-enough working layer

Treat it as `v0.1` with real prototype value.

What is already working well enough to keep building on:
- end-to-end staged flow exists
- planning / dispatch / execution / review are connected
- OpenClaw executor integration exists
- task-level synthesis exists before review
- reviewer is checking delivery quality, not only process state
- stronger executor result semantics are now present
- review can consume executor-side acceptance checks / completion basis / needs-input signals
- failure-path review is less optimistic than the baseline version

## Still weak / not yet fully converged

- executor output remains dependent on prompt and transport quality
- protocol failures and semantic failures still need stricter enforcement over time
- plan shapes are still limited and not yet fully task-shape driven
- schema / docs / runtime usage are closer, but still not perfect SSOT
- mock / validation support logic still needs careful boundary discipline

## Interpretation rules

- Use it when staged orchestration clearly improves quality or controllability.
- Do not force it onto simple work.
- Do not treat orchestration as business truth.
- If user-facing output depends on raw executor output, do one extra sanity pass.
- Prefer explicit send-back over optimistic completion when delivery evidence is weak.
