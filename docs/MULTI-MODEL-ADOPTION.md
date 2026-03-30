# Multi-model adoption guide

This note explains how `multi-agent-lite` should be absorbed as a practical multi-model production framework rather than treated as a novelty demo.

## Positioning

`multi-agent-lite` is best used as an **internal production chain** for higher-quality project work:
- clearer planning,
- better separation between research / execution / review,
- stronger auditability,
- lower single-pass failure rate.

It should not be mistaken for the final business framework itself.
Its first job is to improve how the agent works internally.

## Recommended operating principle

Use the framework as a **quality multiplier** when a task benefits from role separation.

### Single-model path

Prefer a direct single-agent path when:
- the task is small,
- the answer is mainly explanatory,
- there is no meaningful gain from role separation,
- the cost of orchestration exceeds the value.

### Multi-model path

Prefer `multi-agent-lite` when the task has at least one of these traits:
- requires planning before execution,
- needs web / doc / code / rule synthesis,
- produces code, workflow, or structured deliverables,
- benefits from an explicit review pass,
- is important enough that one-shot mistakes are costly.

## Default role responsibilities

### manager
Responsible for:
- framing the task,
- deciding scope,
- choosing whether orchestration is justified,
- defining acceptance criteria,
- deciding whether the task should be sent back for replanning.

### research
Responsible for:
- collecting missing context,
- reading docs / repos / references,
- extracting constraints and differences,
- reducing ambiguity before execution.

### execution
Responsible for:
- generating concrete outputs,
- writing code / rules / mappings / structured artifacts,
- following acceptance constraints instead of expanding scope.

### reviewer
Responsible for:
- checking whether output matches the acceptance criteria,
- identifying risks, omissions, and weak assumptions,
- deciding approve vs send-back,
- protecting final output quality.

## Recommended activation thresholds

### Use direct mode
- casual Q&A,
- tiny edits,
- simple lookups,
- low-risk guidance.

### Use manager + execution + reviewer
- medium-complexity implementation tasks,
- drafting structured deliverables,
- code or workflow tasks with a real quality bar.

### Use manager + research + execution + reviewer
- ambiguous project tasks,
- repo / framework study,
- tasks that combine reading + synthesis + implementation,
- tasks where source grounding matters.

## Why this matters in a multi-model environment

If multiple models are available, forcing one model to do planning, research, execution, and review in one pass wastes the environment.

A staged chain provides:
- specialization,
- easier failure localization,
- cleaner intermediate artifacts,
- more reliable final outputs.

## Enterprise delivery interpretation

For business-facing projects, the framework should be treated as:
- a task production pipeline,
- not the source of business truth.

Business truth should stay in:
- rules,
- templates,
- mappings,
- validation criteria,
- project-specific configuration.

The framework only organizes how those assets are produced and checked.

## Mapping to logistics import work

A practical mapping looks like this:

- `manager` → classify project family, define current-stage objective, freeze scope
- `research` → read templates, collect field differences, identify project-specific rules
- `execution` → generate mappings, normalized tables, cleaning logic, import artifacts
- `reviewer` → verify field completeness, formatting compliance, and import readiness

## Current gaps to improve next

The repo already has a usable skeleton, but these additions would make it more production-friendly:

1. explicit task-size routing rules,
2. acceptance-criteria templates,
3. reviewer checklists by task type,
4. stronger artifact validation,
5. richer failure / fallback reporting,
6. project-facing examples.

## Recommendation

Adopt this framework as a **controlled internal multi-model work mode**.
Do not oversell it as a full autonomous multi-agent platform.

Its practical strength is disciplined staged execution.
