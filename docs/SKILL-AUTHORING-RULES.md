# Skill authoring rules

## Goal
Keep this repository usable as the number of skills grows.

## Rules

1. Every skill must have a concise `SKILL.md` with clear trigger conditions.
2. Detailed material should move to `references/`, not bloat the main skill body.
3. Reusable code belongs in `frameworks/`, not duplicated across multiple skills.
4. Keep naming consistent: lowercase-hyphen-case.
5. If a skill depends on a framework, document that relationship explicitly.
6. Prefer one clear source of truth instead of parallel copies.
7. Before adding a new top-level folder, check whether it belongs under `skills/`, `frameworks/`, or `docs/`.

## For multi-agent-lite specifically

- The skill is the routing and workflow layer.
- The framework code is the implementation layer.
- Do not merge the two into one overloaded folder.
