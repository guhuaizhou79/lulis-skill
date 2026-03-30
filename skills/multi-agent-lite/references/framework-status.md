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

## Current maturity

Treat it as `v0.1`.

The main chain already has real prototype value, but the executor contract and real runtime stability still have tail risk. This should be described as an internal or controlled-trial framework, not as a mature production platform.

## What is working

- end-to-end staged flow exists
- OpenClaw executor integration exists
- planning / dispatch / execution / review are connected
- reviewer is starting to check delivery quality, not only process state

## What is still weak

- executor output remains dependent on prompt and transport quality
- protocol failures and semantic failures still need stricter enforcement over time
- plan shapes are still limited and not yet fully task-shape driven
- some maturity / routing truths still need further SSOT cleanup across the repo

## Interpretation rules

- Use it when staged orchestration clearly improves quality or controllability.
- Do not force it onto simple work.
- Do not treat orchestration as business truth.
- If user-facing output depends on raw executor output, do one extra sanity pass.
