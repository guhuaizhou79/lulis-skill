# responses-image-endpoint

A small OpenClaw framework for probing and using a custom OpenAI-compatible Responses image endpoint.

## What it is

`responses-image-endpoint` is a bounded framework for:
- probing route and auth compatibility
- distinguishing bad route vs auth vs model-path failures
- optional prompt optimization
- streaming image generation through `image_generation`
- saving image and metadata outputs in a structured way

It is especially useful for third-party relays that claim OpenAI compatibility but behave differently during image streaming.

## What it is not

It is not:
- a replacement for built-in local image workflows
- a secret store
- a universal OpenAI SDK wrapper
- a general asset pipeline manager

## Files

- `responses_image_api.py` -> shared request, error, and SSE parsing logic
- `probe_endpoint.py` -> probe-first compatibility entrypoint
- `generate_image.py` -> prompt optimization plus image generation entrypoint

## Usage

Probe a route first:

```bash
python frameworks/responses-image-endpoint/probe_endpoint.py \
  --endpoint "https://example.com/v1/responses" \
  --api-key "sk-..." \
  --text-model "gpt-5.4" \
  --image-model "gpt-image-2"
```

Generate an image after a healthy probe:

```bash
python frameworks/responses-image-endpoint/generate_image.py \
  --endpoint "https://example.com/v1/responses" \
  --api-key "sk-..." \
  --text-model "gpt-5.4" \
  --image-model "gpt-image-2" \
  --prompt "A fluffy white cat sitting by a wooden window in warm morning light, realistic photography."
```

## Validation

Quick checks:

```bash
python -m py_compile frameworks/responses-image-endpoint/responses_image_api.py \
  frameworks/responses-image-endpoint/probe_endpoint.py \
  frameworks/responses-image-endpoint/generate_image.py
```

```bash
python frameworks/responses-image-endpoint/probe_endpoint.py --help
python frameworks/responses-image-endpoint/generate_image.py --help
```

## Notes

This folder holds the implementation code.
The triggerable OpenClaw skill lives in `../../skills/responses-image-endpoint/`.
