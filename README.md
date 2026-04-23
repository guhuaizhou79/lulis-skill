# lulis-skill

A shared repository for reusable OpenClaw skills, supporting framework code, and merged agent tooling history.

## What is here

This repository started as a shared home for reusable OpenClaw skills and their supporting frameworks. It now also contains additional agent runtime, gateway, CLI, web, and test assets that arrived through a merged development branch.

The practical split is:

- `skills/` -> triggerable OpenClaw skills
- `frameworks/` -> reusable implementation code used by skills
- `docs/` -> repo-wide structure and authoring rules for the skill/framework layer
- top-level runtime folders such as `agent/`, `gateway/`, `hermes_cli/`, `tools/`, `web/`, and `website/` -> merged agent and platform code

## Current skill and framework contents

- `skills/multi-agent-lite/` -> lightweight multi-agent orchestration skill
- `skills/responses-image-endpoint/` -> custom Responses image gateway skill
- `frameworks/multi-agent-lite/` -> framework implementation behind the orchestration skill
- `frameworks/responses-image-endpoint/` -> probe and generation implementation for custom image routes

## Rule of thumb

- Put workflow guidance and trigger rules in `skills/`
- Put reusable skill implementation code in `frameworks/`
- Put repo conventions in `docs/`
- Keep larger runtime or platform code outside the skill folders

## See also

- `docs/REPO-STRUCTURE.md`
- `docs/SKILL-AUTHORING-RULES.md`
