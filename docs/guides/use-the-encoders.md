# Use the encoders

This guide is for perception service users: you end up with the MedOmni gateway running locally and your own code calling encoders over HTTP.

## Before you start

- A checkout of v0.2.0, Docker, and [uv](https://docs.astral.sh/uv/).
- Inputs in a supported family. Each encoder reads exactly one family; see [Encoders](../catalog/encoders.md) and [Families](../learn/contracts/families.md).
- A GPU for some encoders. Each encoder's card says what it needs.

## Steps

1. Build the images you need. You do not need all of them. Images are built locally and tagged `:dev`.

    ```bash
    uv run perception/registry.py build ecg-12lead-500hz-mv__ecgfounder
    ```

2. Start the gateway, pointing it at the folder that holds your inputs. It is mounted read-only into every encoder container.

    ```bash
    uv run perception/gateway/main.py --data-root ~/samples
    ```

    It listens on `127.0.0.1:8000`. Pool size, timeouts and the image tag are set in `perception/deployment.yaml`.

3. List the encoders and read a card before you rely on an encoder.

    ```bash
    curl "localhost:8000/encoders?family=ecg-12lead-500hz-mv"
    ```

    ```bash
    curl localhost:8000/cards/ecg-12lead-500hz-mv__ecgfounder
    ```

4. Send an input and read the evidence. The path is relative to the data root.

    ```bash
    curl -X POST localhost:8000/encode -H "Content-Type: application/json" -d '{"encoder_id": "ecg-12lead-500hz-mv__ecgfounder", "path": "ecg/record.hea"}'
    ```

To try a single encoder without the gateway, the rule-based vitals encoder needs no weights:

```bash
uv run perception/registry.py build clinical-measurement-irregular__rule-vitals
```

```bash
python3 perception/encoders/clinical-measurement-irregular/rule-vitals/demo.py --baked
```

## Check

A successful `encode` returns evidence: the encoder's native outputs, wrapped with what a reader needs to weigh them (provenance, reliability, limits from the card). The first call to an encoder is slow while its container starts; `runtime.container_start_ms` in the response says how slow. The request and response shapes are in [Service API](../learn/contracts/service-api.md).

## Where next

- [Card](../learn/contracts/card.md): what a card declares.
- [Encoders](../catalog/encoders.md): every encoder in this version.
- [Contribute](contribute.md): add an encoder for a new family.
