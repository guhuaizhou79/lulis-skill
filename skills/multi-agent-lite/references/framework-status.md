# Framework status

## Current definition

`multi-agent-lite` is the lightweight multi-agent collaboration framework built in the workspace.

It currently supports:
- task creation,
- planning,
- role-based dispatch,
- executor adapter execution,
- review loop,
- done / send-back flow.

## Current role set

- manager
- research
- execution
- reviewer

## Current model routing

- manager → `gpt-5.4`
- research → `claude-sonnet-4-20250514`
- execution_code → `gpt-5-codex`
- execution_general → `gpt-5.4`
- reviewer → `o3`

## Current maturity

Treat it as `v0.1`:
- the main chain is real and usable,
- the OpenClaw executor is connected,
- a remaining tail exists in Chinese text display/encoding quality.

## Practical guidance

Use it when staged orchestration adds value.
Do not force it onto simple tasks.
If consuming raw executor output for user-facing prose, perform one extra clean-up/sanity pass.
