# Repository structure for lulis-skill

This repository is the long-term home for reusable OpenClaw skills and the framework code they depend on.

## Standard structure

```text
skills/
  multi-agent-lite/
  ...future skills...
frameworks/
  multi-agent-lite/
docs/
  REPO-STRUCTURE.md
  SKILL-AUTHORING-RULES.md
```

## Placement rules

### `skills/`
Use for triggerable AgentSkills only.
Each skill should contain only:
- `SKILL.md`
- `references/` (optional)
- `scripts/` (optional)
- `assets/` (optional)

Do not stuff full framework code directly inside a skill folder.

### `frameworks/`
Use for larger reusable implementations.
Examples:
- orchestrators
- runtimes
- adapters
- schemas
- configs
- framework docs

### `docs/`
Use for repository-wide conventions.
Examples:
- naming rules
- authoring rules
- lifecycle rules
- sync rules

## Naming guidance

- skill folders: lowercase-hyphen-case
- framework folders: lowercase-hyphen-case
- avoid spaces, mixed naming styles, and one-off ad-hoc folders

## Maintenance rule

If a future addition is reusable beyond one skill, move it to `frameworks/` or `docs/` instead of bloating a single skill folder.
