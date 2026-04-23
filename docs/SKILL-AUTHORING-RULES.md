# Skill authoring rules

## Goal
Keep this repository focused, reusable, and easy to maintain as the skill set grows.

## Rules

1. Every skill must have a concise `SKILL.md` with clear trigger conditions.
2. Detailed material should go to `references/`, not bloat the main skill body.
3. Helper code that belongs to one skill should stay in that skill's `scripts/` folder.
4. Reusable implementation shared across skills belongs in `frameworks/`.
5. Keep naming consistent: lowercase-hyphen-case.
6. Prefer one clear source of truth instead of parallel copies.
7. Before adding a new top-level folder, check whether it really belongs under `skills/`, `optional-skills/`, `frameworks/`, or `docs/`.
8. Do not reintroduce unrelated runtime, gateway, web, or test trees into this repository.
