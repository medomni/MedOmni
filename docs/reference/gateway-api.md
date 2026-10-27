# Service API

The Service API is the HTTP interface between an agent and the encoders: find an encoder, read its card, and send it an input to get evidence back.

Version: v1 · Schema: `medomni/contracts/schemas/{encode-request,evidence}.schema.json`

!!! note "Draft"
    Today the gateway is `perception/gateway/` and the spec is `perception/spec/service-api.md`. The schemas are frozen as v1 in roadmap phase 2 and move with the gateway to the encoder repository in phase 5.

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

## Check

```bash
medomni encoder check encoders/<family>/<encoder>
```

Today: the gateway tests in `perception/tests/test_gateway_api.py`.

## Where next

- [Card](card.md): what the `card` field holds.
- [Use the encoders](../../guides/use-the-encoders.md): call the gateway.
- [Encoders](../../catalog/encoders.md): what you can call.
