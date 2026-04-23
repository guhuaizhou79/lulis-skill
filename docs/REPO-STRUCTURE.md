# Repository structure for lulis-skill

This repository is the long-term home for reusable skills and the minimal shared framework code that some skills depend on.

## Standard structure

```text
skills/
optional-skills/
frameworks/
docs/
```

## Placement rules

### `skills/`
Use for bundled triggerable skills.
Each skill may contain:
- `SKILL.md`
- `references/`
- `scripts/`
- `templates/`
- `assets/`

### `optional-skills/`
Use for official but non-default skills.
They follow the same internal structure rules as `skills/`.

### `frameworks/`
Use only for shared implementation that is reused by one or more skills and is too large to live comfortably inside a single skill directory.

### `docs/`
Use for repository-wide governance and authoring conventions.

## Naming guidance

- skill folders: lowercase-hyphen-case
- framework folders: lowercase-hyphen-case
- avoid ad-hoc top-level product/runtime folders

## Maintenance rule

If new content is not directly serving a skill, it probably does not belong in this repository.
