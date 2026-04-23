# lulis-skill

A repository focused on reusable AgentSkills and the small framework code they explicitly depend on.

## What is here

This repo now keeps only the skill-layer content:

- `skills/` -> bundled skills
- `optional-skills/` -> official optional skills
- `frameworks/` -> small reusable framework code used by specific skills
- `docs/` -> repo conventions for skill and framework organization

## What was removed

Non-skill agent runtime, gateway, CLI, web app, platform adapters, large test trees, and unrelated execution infrastructure were removed so this repository stays focused on skill authoring and maintenance.

## Repository rules

- Put trigger instructions in `SKILL.md`
- Put detailed references in `references/`
- Put reusable helper code in `scripts/`
- Put reusable templates/assets next to the skill when they are part of the skill itself
- Put larger shared implementation only in `frameworks/`
- Avoid adding unrelated top-level runtime code back into this repo

## Current top-level layout

```text
skills/
optional-skills/
frameworks/
docs/
```

## See also

- `docs/REPO-STRUCTURE.md`
- `docs/SKILL-AUTHORING-RULES.md`
