---
name: responses-image-endpoint
description: Use when the user wants image generation through a custom OpenAI-compatible Responses endpoint and API key, especially when the route must be probed first to confirm auth, JSON routing, or image_generation compatibility. Do not use for normal built-in image generation when no custom gateway is involved.
---

# Responses Image Endpoint

Use this skill when a task depends on a user-provided Responses-compatible image API instead of the default local image workflow.

## Route into this skill when

Trigger when the user wants one or more of these patterns:
- generate an image through a custom endpoint URL and API key
- verify whether a relay or proxy really supports `image_generation`
- debug why a Responses-compatible image route is failing
- test which text model and image model combination works on a third-party gateway
- run prompt optimization plus image generation against a custom Responses route

Typical requests:
- "Use my endpoint and key to generate an image"
- "Check whether this proxy supports gpt-image-2"
- "Probe this /v1/responses route before trying generation"
- "My relay says it is OpenAI compatible; verify image_generation"

## Do not route into this skill when

Stay out of this skill when any of these is true:
- the user only wants normal built-in image generation
- the task is image editing inside the default OpenClaw image workflow
- there is no custom endpoint, no API key, and no relay compatibility question
- the task is mainly UI asset creation and does not depend on an external custom gateway

## Why use it

Use `responses-image-endpoint` to gain:
- route-first compatibility checking
- clearer separation between auth errors, bad routes, and model-pool failures
- a repeatable CLI path for probe -> optimize -> generate
- structured JSON results instead of ad-hoc terminal logs

This skill is useful for custom relays because a route can look "OpenAI compatible" for text while still failing during streaming image generation.

## Workflow

1. Collect the endpoint URL and API key. Do not store secrets in repo files.
2. Prefer probing the exact route the user provided before claiming it is usable.
3. If the user only gives a base URL, check whether `/v1/responses` is the real JSON API route.
4. Run the framework probe first:
   `python frameworks/responses-image-endpoint/probe_endpoint.py ...`
5. Read the JSON result before proceeding.
6. Only run generation after the probe shows a healthy route:
   `python frameworks/responses-image-endpoint/generate_image.py ...`
7. Return:
   - the final image path
   - the final prompt actually used for image generation
   - the compatibility conclusion in plain language

## Operating rules

- Never hardcode or commit a user API key.
- If the endpoint returns HTML or other non-JSON content, treat it as a route problem first.
- If text probing succeeds but image probing fails, report that auth and base routing are likely healthy and the failure is probably inside `image_generation`, relay compatibility, or upstream model access.
- If image generation fails after a partial stream, do not immediately declare the endpoint unsupported. Some relays close SSE streams in non-standard ways.
- Prefer structured CLI output over free-form guesswork.

## Framework relationship

This skill depends on:
- `frameworks/responses-image-endpoint/`

The skill is the routing and workflow layer.
The framework code is the implementation layer.

## Read only when needed

- `references/usage-guide.md` -> CLI usage, environment variables, and error interpretation
- `../../frameworks/responses-image-endpoint/README.md` -> framework scope and validation path
