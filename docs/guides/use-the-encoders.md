# Use the encoders

This guide is for perception service users: you end up with the MedOmni gateway running locally and your own code calling encoders over HTTP.

!!! note "Draft"
    Published images on ghcr.io and the `medomni` perception client arrive in v1.0.0 (roadmap phases 3 and 5).

## Before you start

- MedOmni installed, and Docker.
- Inputs in a supported family. Each encoder reads exactly one family; see [Encoders](../catalog/encoders.md) and [Families](../learn/contracts/families.md).
- A GPU for some encoders. Each encoder's card says what it needs.

## Steps

1. Pull the images you need. You do not need all of them.

    ```bash
    medomni encoders pull ecg-12lead-500hz-mv
    ```

2. Start the gateway.

    ```bash
    medomni gateway up
    ```

3. List the encoders and read a card before you rely on an encoder.

    ```bash
    curl "localhost:8080/encoders?family=ecg-12lead-500hz-mv"
    ```

    ```bash
    curl localhost:8080/cards/ecg-12lead-500hz-mv__ecgfounder
    ```

4. Send an input and read the evidence. The path is relative to the data folder the gateway serves.

    ```bash
    curl -X POST localhost:8080/encode -H "Content-Type: application/json" -d '{"encoder_id": "ecg-12lead-500hz-mv__ecgfounder", "path": "ecg/record.hea"}'
    ```

## Check

A successful `encode` returns evidence: the encoder's native labels, wrapped with what a reader needs to weigh them (provenance, reliability, limits from the card). The request and response shapes are in [Service API](../learn/contracts/service-api.md).

## Where next

- [Card](../learn/contracts/card.md): what a card declares.
- [Encoders](../catalog/encoders.md): every encoder in this version.
- [Contribute](contribute.md): add an encoder for a new family.
