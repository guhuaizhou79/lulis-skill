# lulis-skill

A shared repository for reusable OpenClaw skills, supporting framework code, and repo-level governance.

## Layout

- `skills/` → triggerable AgentSkills
- `frameworks/` → reusable implementation code used by skills
- `docs/` → repository-wide structure and authoring rules

## Current contents

- `skills/multi-agent-lite/` → lightweight multi-agent orchestration skill
- `frameworks/multi-agent-lite/` → framework implementation behind the skill

## Rule of thumb

- Put workflow guidance and trigger rules in `skills/`
- Put reusable code in `frameworks/`
- Put repo conventions in `docs/`

See:
- `docs/REPO-STRUCTURE.md`
- `docs/SKILL-AUTHORING-RULES.md`
