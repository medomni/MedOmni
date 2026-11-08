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
    ├── input.*         synthetic or openly licensed, written by medomni studio testdata
    ├── expected.json   the recorded responses, written by --freeze
    └── PROVENANCE.md   written by medomni studio testdata
```

The runtime in `src/medomni/perception/runtime/` is built into every image. It declares the encoder interface, `load` and `encode`, and serves it through the container API. It reads each family's files with one decoder per family, and uses Core's families module for aliases, labels and format checks.

An encoder author writes only `load` and `encode`; the check fails an adapter that does not implement them. Everything else is shared by every encoder: asset preparation, which the image build runs; the encoder tests in `tests/perception/`; and two [Studio](../studio/overview.md) tools, `medomni studio encoder-demo` and `medomni studio testdata`.

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

It runs four stages in order and stops at the first failure:

1. **Card:** validates the model card, as `medomni contracts check` does, and the folder.
2. **Build:** builds the image.
3. **Test data:** runs the image on `testdata/` and compares the responses with `expected.json`.
4. **Real samples:** runs the image offline on real samples of its family and checks each response against the model card. It needs at least three samples, from the family's published samples or `--samples <dir>`. With fewer, the stage reports "unverified" instead of passing.

Stages 3 and 4 run the encoder's tests in `tests/perception/`. `--freeze` records `expected.json` from the current build; a later change that alters the responses fails stage 3.

## Images

- One image per encoder, at `ghcr.io/medomni/<encoder>`, tagged with the MedOmni version that built it.
- Users pull images; they never install encoder code.
- Licenses differ; the [Encoders reference](../../reference/encoders.md) lists each one.

## Where it lives

- `perception/encoders/<family>/<encoder>/`: each encoder
- `src/medomni/perception/runtime/`: the serving code shared by every image, with one decoder per family in `decoders/`
- `src/medomni/perception/registry/`: the catalogue, image builds and pulls
- `tests/perception/`: the encoder tests the check runs

## Where next

- [Encoders reference](../../reference/encoders.md): model card fields and every encoder in this version.
- [Gateway](gateway.md): how encoders are found and called.
- [Families](../core/families.md): what an encoder reads.
