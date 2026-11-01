# Gateway

The gateway is one HTTP service in front of every encoder. Through it, an agent or your own code finds encoders, reads their model cards and runs them. It only finds, describes and runs encoders: the agent decides which to call and how to combine their evidence.

```text
caller ──GET /encoders, /cards──▶ catalogue (no containers needed)
caller ──POST /encode──▶ pool ──▶ encoder container ──▶ evidence
```

## Find

Model cards are files, so the gateway loads every card at start. Searching and reading cards start no containers.

- `GET /encoders` searches by text, family, modality, output kind or label.
- `GET /cards/{encoder_id}` returns one model card.
- `GET /families` lists each family with its encoder count.

## Run

`POST /encode` sends one input to one encoder. Only this call uses a container.

- The first call to an encoder starts its container; later calls reuse it.
- A limit caps the number of live containers. When the limit is reached, the least recently used idle container stops.
- A busy container is never stopped.
- Idle containers stop after a timeout.

The response reports the start time in `runtime.container_start_ms`.

## Evidence

Each `encode` returns evidence:

- the encoder's outputs, unchanged
- provenance: hashes of the input, weights and image
- the reliability and limits from the model card
- a fingerprint of encoder, weights, image, input and options

Evidence contains only the model card and the container's reply. Identical requests give identical fingerprints and are served from a cache.

## Start it

```bash
medomni perception up --data-root <dir>
```

It reads inputs from your data root, mounted read-only. Inside Bench's atom tasks, Bench starts the gateway behind its [sidecar](../bench/runs.md#inside-an-atom-task), which adds a call budget, a family filter and a call log. The gateway itself has none of these.

## Where it lives

- `src/medomni/perception/gateway/`: the service, built into the gateway image

## Where next

- [Gateway API](../../reference/gateway-api.md): every endpoint, field and error code.
- [Use the encoders](../../guides/use-the-encoders.md): start the gateway and call it.
- [Runs](../bench/runs.md): how Bench uses the gateway inside an atom task.
