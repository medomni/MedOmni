# Use the encoders

For encoder users. You run Perception's gateway locally and call encoders over HTTP from your own code.

## Before you start

- MedOmni installed, and Docker.
- Inputs in a supported family. Each encoder reads exactly one family; see [Encoders](../reference/encoders.md) and [Families](../reference/families.md).
- A GPU for some encoders. Each encoder's model card says what it needs.

## Steps

1. Build the image of each encoder you need. The check builds it and runs it on the encoder's test data.

    ```bash
    medomni perception check perception/encoders/ecg-12lead-500hz-mv/ecgfounder
    ```

2. Start the gateway on the built encoders, pointing it at the folder that holds your inputs. The folder is mounted read-only into every encoder container.

    ```bash
    medomni perception up --data-root ~/samples
    ```

    It listens on `127.0.0.1:8000`.

3. List the encoders and read a model card before you rely on an encoder.

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

## Check

A successful `encode` returns evidence: the encoder's outputs with their provenance, and the reliability and limits from the model card. The first call to an encoder waits for its container to start; the response reports the wait in `runtime.container_start_ms`. The request and response shapes are in [Gateway API](../reference/gateway-api.md).

## Where next

- [Encoders](../reference/encoders.md): the model card format and every encoder in this version.
- [Add an encoder](add-an-encoder.md): package a new encoder for a family.
