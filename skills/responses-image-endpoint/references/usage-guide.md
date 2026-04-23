# Usage guide

This note explains how to use the `responses-image-endpoint` skill in a real OpenClaw workflow.

## Good fits

Use this skill when:
- the user provides a custom endpoint URL and API key
- the endpoint is a relay, proxy, or compatibility layer
- route validity is uncertain
- the user wants to know whether `gpt-image-1` or `gpt-image-2` actually works on that route
- the task needs a reproducible probe result before a real image job

## Poor fits

Avoid this skill when:
- built-in image generation is enough
- there is no custom gateway question
- the task is simple image ideation with no external API dependency

## Environment variables

The framework supports:
- `RESPONSES_IMAGE_ENDPOINT`
- `RESPONSES_IMAGE_API_KEY`

That lets you avoid echoing secrets directly into long commands.

## Probe first

Example:

```bash
python frameworks/responses-image-endpoint/probe_endpoint.py \
  --endpoint "https://example.com/v1/responses" \
  --api-key "sk-..." \
  --text-model "gpt-5.4" \
  --image-model "gpt-image-2"
```

What the probe tells you:
- whether the route returns API JSON
- whether auth is accepted
- whether text Responses works
- whether image generation looks ready

## Generate only after a healthy probe

Example:

```bash
python frameworks/responses-image-endpoint/generate_image.py \
  --endpoint "https://example.com/v1/responses" \
  --api-key "sk-..." \
  --text-model "gpt-5.4" \
  --image-model "gpt-image-2" \
  --prompt "A fluffy white cat sitting by a wooden window in warm morning light, realistic photography."
```

## Error interpretation

### `html_response`

Usually means:
- wrong route
- console page instead of API
- base domain used instead of `/v1/responses`

### `auth_error`

Usually means:
- missing key
- invalid key
- blocked key
- gateway-side auth rejection

### `image_generation_unavailable`

Usually means:
- text route works
- image_generation does not
- relay or upstream pool does not expose the requested image model

### `image_generation_uncertain`

Usually means:
- text route works
- image streaming returned something partial or non-standard
- the relay may still support image generation, but the stream format is unusual

## Practical reporting rule

When using this skill for a real user request, always say:
- which endpoint was tested
- which text model was tested
- which image model was tested
- whether text probe passed
- whether image probe passed
- if generation succeeded, where the image was saved
