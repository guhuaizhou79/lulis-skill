# Project usage guide

This note explains how to use `multi-agent-lite` for real project delivery instead of treating it as a generic orchestration demo.

## What this framework is good at

`multi-agent-lite` is strongest when a task needs:
- staged planning,
- role separation,
- structured execution,
- explicit review,
- a traceable path from task to deliverable.

It is especially useful when direct one-shot answers are likely to hide mistakes.

## What this framework is not

It is not:
- a replacement for business rules,
- a substitute for project-specific configuration,
- a guarantee of correctness,
- a reason to over-split tiny tasks.

## Practical use rule

Use the framework only when orchestration creates real value.

### Good fits
- repo learning and structured synthesis,
- implementation tasks with multiple stages,
- document / code / rule generation,
- tasks that require a second-pass review,
- medium or high-value project tasks.

### Bad fits
- one-step factual questions,
- tiny edits,
- casual discussion,
- tasks where the overhead is greater than the gain.

## Suggested operating pattern

### Stage 1: manager
The manager should:
- define the real objective,
- freeze the scope,
- identify what counts as done,
- decide whether research is needed.

### Stage 2: research
The research role should:
- read the needed docs / repo / templates,
- extract constraints,
- reduce ambiguity,
- hand execution a cleaner task.

### Stage 3: execution
The execution role should:
- produce artifacts,
- stay inside scope,
- emit structured outputs,
- make assumptions explicit when unavoidable.

### Stage 4: reviewer
The reviewer should:
- compare outputs against acceptance criteria,
- reject vague or fragile work,
- identify missing checks,
- force a send-back when quality is not yet enough.

## Review checklist ideas

A reviewer pass is more useful when it checks concrete things such as:
- Does the output match the original goal?
- Are acceptance criteria explicitly satisfied?
- Are risks and unknowns called out?
- Is the result reproducible?
- If code was produced, is there a verification path?
- If structured data was produced, is schema / format validity checked?

## Logistics-project interpretation

For logistics import and template-normalization work, a high-value mapping is:

- manager → choose project family and current target output
- research → inspect template differences and field rules
- execution → build mappings, transforms, or import sheets
- reviewer → verify field completeness, format legality, and delivery readiness

This framework should improve the **production process** around those project artifacts.
The domain rules themselves should still live outside the orchestration layer.

## Current recommendation

Treat `multi-agent-lite` as:
- a usable internal work framework,
- a quality-oriented multi-model path,
- a disciplined production chain for complex tasks.

Avoid marketing it as a full autonomous platform until stronger validation and routing discipline exist.
