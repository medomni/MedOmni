# Service API

The Service API is the HTTP interface between an agent and the encoders: find an encoder, read its card, and send it an input to get evidence back.

Defined in: `perception/gateway/schemas.py` (the models the gateway serves) · prose spec `perception/spec/service-api.md` · evidence schema `perception/spec/evidence.schema.json`

The gateway also serves its own OpenAPI page at `/docs`.

## Fields

**Endpoints:**

| Call | Route | Returns |
|---|---|---|
| `list_encoders` | `GET /encoders` with optional `q`, `family`, `modality`, `kind`, `label`, `runnable`, `limit` | Encoder summaries, best match first |
| `get_card` | `GET /cards/{encoder_id}` | The encoder's card, verbatim |
| `encode` | `POST /encode` | Evidence |
| | `GET /families` | Each family with its encoder counts |

**Encode request:**

| Field | Type | Required | Meaning |
|---|---|---|---|
| `encoder_id` | string | yes | `<family>__<name>`. |
| `path` | string | yes | The input, relative to the gateway's data root. |
| `options` | object | no | Encoder options, as declared in its card. |

**Evidence** (the response):

| Field | Type | Required | Meaning |
|---|---|---|---|
| `encoder_id`, `family` | string | yes | Which encoder answered. |
| `healthy` | bool | yes | `false` means the input was degenerate; this is a result, not an error. |
| `outputs` | list | yes | The encoder's native output blocks: `labels`, `events`, `text` or `embedding`. |
| `notes` | list of string | yes | Why the output is degraded, if it is. |
| `reliability` | object or null | yes | The card's reliability block. |
| `card` | object | yes | The card, verbatim. |
| `provenance` | object | yes | `input_sha256`, `input_complete`, `image_id`, and when known `weights_sha256`, `source_rev`, `image`, `image_digest`. |
| `fingerprint` | string | yes | `sha256:` plus 64 hex: the hash of encoder, weights, image, input and options. Identical requests give identical fingerprints. |
| `runtime` | object | yes | `container_start_ms`, `cached`, and optionally `duration_ms`. |

Output blocks: `labels` carries a `scale` (`probability`, `logit`, `score`, `physical`) and items of `label`, `value` and optional `unit`; `events` carries items with `t_start` and `t_end` in seconds from the start of the recording.

## Rules

- Unknown request fields are rejected (422).
- Unknown encoder: 404. Path outside the data root or missing: 400. Card-only encoder: 409. Container crash or a reply naming the wrong encoder or family: 502. No free slot: 503.
- Evidence is composed from the card and the container's reply; the gateway never invents outputs.
- Inside a task the perception sidecar adds three rules: a call budget (`MAX_CALLS`, 300 in `enc`, 1000 in `enc-forced`), a catalogue scoped to the families staged for that patient, and a call log at `GET /usage` that the harness copies into the trial for scoring.

## Check

```bash
uv run --with fastapi --with httpx --with pyyaml --with pydantic python -m unittest discover -s perception/tests -p test_gateway_api.py
```

## Where next

- [Card](card.md): what the `card` field holds.
- [Use the encoders](../../guides/use-the-encoders.md): call the gateway.
- [Encoders](../../catalog/encoders.md): what you can call.
