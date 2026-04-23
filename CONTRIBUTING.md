# Contributing to lulis-skill

This repository is for maintaining reusable skills and the small shared framework code they depend on.

## Contribution priorities

1. Improve existing skills
2. Add missing references, scripts, templates, or assets that make a skill actually usable
3. Keep framework code minimal and clearly tied to skills
4. Improve repository structure and authoring consistency
5. Remove duplication and stale content

## Repository scope

Please keep contributions inside these areas:

- `skills/`
- `optional-skills/`
- `frameworks/`
- `docs/`

Do not add unrelated agent runtime, gateway, web app, or large general-purpose infrastructure back into this repository.

## Skill structure

A skill should usually contain:

- `SKILL.md`
- optional `references/`
- optional `scripts/`
- optional `templates/`
- optional `assets/`

## Framework structure

Use `frameworks/` only when implementation is shared or too large to keep inside one skill folder.

## Rule of thumb

If a file does not directly help author, run, document, or support a skill, it probably should not live here.
