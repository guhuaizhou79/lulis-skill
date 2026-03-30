# multi-agent-lite

A lightweight multi-agent collaboration framework for OpenClaw.

## What it is

A staged orchestration path built around:
- manager
- research
- execution
- reviewer

## Current flow

`create task -> plan -> dispatch -> execute -> review -> done / send back`

## Current maturity

Treat this as `v0.1`:
- main chain works,
- OpenClaw executor is connected,
- there is still a known Chinese output display/encoding quality tail.

## Notes

This folder holds the framework implementation.
The triggerable skill lives in `../../skills/multi-agent-lite/`.
