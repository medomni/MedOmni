# Gateway API

Every endpoint, field and error code of the gateway. [Gateway](../learn/perception/gateway.md) explains how it works.

Contract: Gateway API, `src/medomni/core/contracts/schemas/gateway-api.schema.json`, with the evidence in `evidence.schema.json`.

The gateway also serves its own OpenAPI page at `/docs`.

## Fields

**Endpoints:**

| Call | Route | Returns |
|---|---|---|
| `list_encoders` | `GET /encoders` with optional `q`, `family`, `modality`, `kind`, `label`, `runnable`, `limit` | Encoder summaries, best match first |
| `get_card` | `GET /cards/{encoder_id}` | The encoder's model card, verbatim |
| `encode` | `POST /encode` | Evidence |
| | `GET /families` | Each family with its encoder counts |

**Encode request:**

| Field | Type | Required | Meaning |
|---|---|---|---|
| `encoder_id` | string | yes | `<family>__<name>`. |
| `path` | string | yes | The input, relative to the gateway's data root. |
| `options` | object | no | Encoder options, as declared in its model card. |

**Evidence** (the response):

| Field | Type | Required | Meaning |
|---|---|---|---|
| `encoder_id`, `family` | string | yes | Which encoder answered. |
| `healthy` | bool | yes | `false`: the input was degenerate. This is a valid result. |
| `outputs` | list | yes | The encoder's native output blocks: `labels`, `events`, `text` or `embedding`. |
| `notes` | list of string | yes | Why the output is degraded, if it is. |
| `reliability` | object or null | yes | The model card's reliability block. |
| `card` | object | yes | The model card, verbatim. |
| `provenance` | object | yes | `input_sha256`, `input_complete`, `image_id`, and when known `weights_sha256`, `source_rev`, `image`, `image_digest`. |
| `fingerprint` | string | yes | `sha256:` plus 64 hex: the hash of encoder, weights, image, input and options. Identical requests give identical fingerprints. |
| `runtime` | object | yes | `container_start_ms`, `cached`, and optionally `duration_ms`. |

Output blocks:

- `labels`: a `scale` (`probability`, `logit`, `score` or `physical`) and items of `label`, `value` and optional `unit`
- `events`: items with `t_start` and `t_end`, in seconds from the start of the recording

## Rules

- Unknown request fields are rejected (422).
- Unknown encoder: 404. Path outside the data root or missing: 400. Encoder with a model card but no image: 409. Container crash or a reply naming the wrong encoder or family: 502. No free slot: 503.

## Check

MedOmni's tests check the gateway against this contract on every pull request. Requests and replies are messages, not files in the repository, so `medomni contracts check` does not read them.

## Where next

- [Encoders](encoders.md): the model card format and what you can call.
- [Use the encoders](../guides/use-the-encoders.md): call the gateway.
