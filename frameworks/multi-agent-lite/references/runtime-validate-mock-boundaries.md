# Runtime / validation / mock boundaries

## Purpose

Prevent convergence drift while preparing `multi-agent-lite` for repo intake.

The framework now has three closely related layers:
- runtime path
- validation path
- mock path

These must support each other, but they must not silently redefine each other.

## 1. Runtime path

Runtime path means the actual staged orchestration flow used for real work:
- task creation
- planning
- dispatch
- execution via real executor when available
- review
- done / send-back

Runtime truth should be defined by:
- task state transitions
- executor contract
- review decision logic
- task-level delivery synthesis

## 2. Validation path

Validation path means scenario-driven checks that confirm the framework behaves as expected.

Examples:
- `validate_delivery.py`
- compile / schema sanity checks
- scenario cases like:
  - deliverable-required
  - failure-semantic-error
  - choice-answering-shape
  - path-lookup-shape

Validation should verify runtime assumptions.
It should not become the reason runtime semantics drift in hidden ways.

## 3. Mock path

Mock path means local fallback behavior used when a real executor is unavailable or when deterministic validation is needed.

Mock is allowed to:
- materialize synthetic artifacts
- simulate answer-shape outputs
- return structured contract fields for testing and local iteration

Mock must not:
- redefine what counts as real production evidence
- silently loosen runtime completion standards
- replace clear runtime-vs-fallback communication

## Intake guidance

When preparing repo intake:
- keep runtime truth in runtime-facing files
- keep validation scenarios in validation-facing files
- keep mock-only conveniences explicit
- if a rule exists only to make tests easier, do not automatically promote it into runtime truth

## Practical rule

When uncertain whether a behavior belongs in runtime or mock:
- if it changes review or delivery decisions for real work, treat it as runtime-sensitive
- if it only helps deterministic local verification, treat it as validation/mock support
