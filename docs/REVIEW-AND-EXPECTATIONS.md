# Review and task-type expectations

`multi-agent-lite` now begins to connect two ideas that were previously too loose:
- task type should influence what the framework expects,
- reviewer logic should check more than process completeness.

## Task-type expectations

The framework now defines lightweight expectations for task families such as:
- `code`
- `framework_design`
- `automation`
- `general`

These expectations currently influence:
- default execution role,
- whether meaningful execution changes are required,
- whether artifacts are preferred,
- whether the task tends toward stricter review.

## Reviewer improvement

The reviewer still checks process integrity, including:
- assigned model presence,
- completion status,
- parse errors,
- executor errors.

But it now also begins checking basic delivery-quality signals:
- whether execution produced meaningful changes when expected,
- whether execution produced artifacts or changes for artifact-oriented task types,
- whether task acceptance is explicitly present,
- whether risk reporting is visible.

## Why this matters

Without task-type expectations, the planner and reviewer remain too generic.
Without stronger review, the framework can confirm that a process ran without confirming that the output is useful.

This change does not make the framework fully mature.
It does make it more aligned with the idea of a real multi-model production chain.
