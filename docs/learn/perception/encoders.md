# Encoders

An encoder is a containerised model or rule that reads one family and returns evidence. Each encoder is one folder in the repository, built into one image, and described by one model card.

```text
perception/encoders/<family>/<encoder>/ ──build──▶ image on ghcr.io/medomni
                         card.yaml ──publish──▶ model card on Hugging Face
```

## The encoder folder

```text
perception/encoders/<family>/<encoder>/
├── adapter.py      load() once, then encode(sample, options)
├── card.yaml       the model card
├── Dockerfile      pinned base image, dependencies, source revision, weight hashes
└── testdata/
    ├── input.*         synthetic or openly licensed
    ├── expected.json   the recorded responses
    └── PROVENANCE.md
```

The runtime in `perception/runtime/` wraps `adapter.py` in the same container API in every image, so an encoder author writes only `load` and `encode`.

## Model card

The model card states an encoder's facts:

- the family it reads and the outputs it returns: `labels`, `events`, `text` or `embedding`
- where it comes from: source, weights, license
- its intended use and known limits
- whether it runs zero-shot, with no training on MedOmni data
- its reliability: `unmeasured` or `measured`, with evidence

Agents read the card through the gateway before they rely on an encoder.

## Check and freeze

```bash
medomni perception check perception/encoders/<family>/<encoder>
```

It validates the card, builds the image, runs it on its test data and compares the responses with `expected.json`. `--freeze` records `expected.json` from the current build; a later change that alters the responses fails the check.

## Images

- One image per encoder, at `ghcr.io/medomni/<encoder>`, tagged with the MedOmni version that built it.
- Users pull images; they never install encoder code.
- Licenses differ; the [Encoders reference](../../reference/encoders.md) lists each one.

## Where it lives

- `perception/encoders/<family>/<encoder>/`: each encoder
- `perception/runtime/`: the serving code shared by every image
- `perception/registry/`: the catalogue, image pulls and the check

## Where next

- [Encoders reference](../../reference/encoders.md): model card fields and every encoder in this version.
- [Gateway](gateway.md): how encoders are found and called.
- [Families](../core/families.md): what an encoder reads.
