# Repo layout guidance

This skill is meant to live in a shared skill repository.

## Recommended top-level structure

```text
skills/
  <skill-name>/
    SKILL.md
    references/
    scripts/
    assets/
frameworks/
  <framework-name>/
    core/
    configs/
    schemas/
    docs/
docs/
  REPO-STRUCTURE.md
  SKILL-AUTHORING-RULES.md
```

## Why this split

- `skills/` contains triggerable OpenClaw skills.
- `frameworks/` contains larger framework codebases used by skills.
- `docs/` contains repo-wide governance so future additions stay tidy.

## Rule of thumb

- Put orchestration instructions in the skill.
- Put implementation code in the framework.
- Put long-lived conventions in docs.
