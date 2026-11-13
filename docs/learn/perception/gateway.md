# Gateway

The gateway is one HTTP service in front of every encoder. Through it, an agent or your own code finds encoders, reads their model cards and runs them. It only finds, describes and runs encoders: the agent decides which to call and how to combine their evidence.

It has three parts:

- **Catalogue:** finds encoders and serves their model cards.
- **Router:** sends each call to a running encoder container.
- **Evidence:** builds the answer and its fingerprint.

```text
caller ──GET /encoders, /cards──▶ catalogue (no containers needed)
caller ──POST /encode──▶ router ──▶ encoder container ──▶ evidence
```

## Catalogue

Model cards are files, so the gateway loads every card at start. Searching and reading cards start no containers.

- `GET /encoders` searches by text, family, modality, output kind or label.
- `GET /cards/{encoder_id}` returns one model card.
- `GET /families` lists each family with its encoder count.

## Router

`POST /encode` sends one input to one named encoder. Only this call uses a container. For each call the router:

1. **Looks up** the encoder in the catalogue. An unknown encoder, or one with a model card but no image, is refused.
2. **Checks its cache.** An identical earlier request is answered from the gateway's own cache, in memory, without a container. The cache lasts while the gateway runs.
3. **Picks a container:**
    - a running one for that encoder, if it is under its concurrency limit
    - otherwise a new one, if the pool is under its limit of live containers
    - otherwise it stops the least recently used idle container and starts a new one
    - otherwise it waits; one encoder is never started twice
4. **Sends** the request to the container through the Container API.
5. **Handles failure:** a container that fails or hangs is taken out, so the next call gets a fresh one.

Calls to several encoders are separate requests and run side by side, within the limits. A busy container is never stopped, and idle containers stop after a timeout.

The router routes by name only. Choosing encoders is the agent's job, and Bench's behaviour metrics measure that choice.

The response reports the start time in `runtime.container_start_ms`.

## Evidence

Each `encode` returns evidence:

- the encoder's outputs, unchanged
- provenance: hashes of the input, weights and image
- the reliability and limits from the model card
- a fingerprint of encoder, weights, image, input and options

Evidence contains only the model card and the container's reply. Identical requests give identical fingerprints and are served from the cache.

## Start it

```bash
medomni perception up --data-root <dir>
```

It reads inputs from your data root, mounted read-only. Inside an atom task, Bench runs the gateway as the [perception service](../bench/runs.md#inside-an-atom-task), adding a call budget, a family filter and a call log. The gateway itself has none of these.

## Where it lives

- `src/medomni/perception/gateway/`: the service, built into the gateway image

## Where next

- [Gateway API](../../reference/gateway-api.md): every endpoint, field and error code.
- [Use the encoders](../../guides/use-the-encoders.md): start the gateway and call it.
- [Runs](../bench/runs.md): how Bench uses the gateway inside an atom task.
