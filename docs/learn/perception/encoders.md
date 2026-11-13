# Encoders

An encoder is a containerised model or rule that reads one family and returns evidence. Each encoder is one folder in the repository, built into one image, and described by one model card.

```text
perception/encoders/<family>/<encoder>/ ──build──▶ image on your machine
                         card.yaml ──publish──▶ model card on Hugging Face
```

## The encoder folder

```text
perception/encoders/<family>/<encoder>/
├── adapter.py      load() once, then encode(sample, options)
├── card.yaml       the model card
├── Dockerfile      pinned base image, dependencies, source revision
├── assets.json     weights and other files the image build fetches, each with its source and sha256 (if any)
└── testdata/
    ├── input.*         synthetic or openly licensed, written by medomni studio testdata
    ├── expected.json   the recorded responses, written by --freeze
    └── PROVENANCE.md   written by medomni studio testdata
```

The runtime in `src/medomni/perception/runtime/` is built into every image. It declares the encoder interface, `load` and `encode`, and serves it through the container API. It reads each family's files with one decoder per family, and uses Core's families module for aliases, labels and format checks.

An encoder author writes only `load` and `encode`; the check fails an adapter that does not implement them. Everything else is shared by every encoder: asset preparation from `assets.json`, which the image build runs (five encoders instead fetch their weights with their own `fetch_assets.py` during the build); the encoder tests in `tests/perception/`; and two [Studio](../studio/overview.md) tools, `medomni studio encoder-demo` and `medomni studio testdata`.

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

It runs six stages in order and stops at the first failure:

1. **Card:** validates the model card, as `medomni contracts check` does, and the folder.
2. **Dockerfile:** before anything is built, every `torch==` install must use the listed build index and a listed version.
3. **Build:** builds the image.
4. **Image torch:** the torch installed in the image, if any, must be the listed build (`+cpu`) at a listed version. A dependency can bring in torch without any Dockerfile line naming it.
5. **Test data:** runs the image on `testdata/` and compares the responses with `expected.json`.
6. **Real samples:** runs the image offline on real samples of its family and checks each response against the model card. It needs at least three, in `--samples <dir>`, such as the files `medomni studio family-samples` writes from your own copy of a dataset. MedOmni publishes no real samples. Without them, the stage reports `UNVERIFIED-no-samples`, or `UNVERIFIED-access-controlled` for a family whose real samples are access-controlled, and the test data stands in.

The list for stages 2 and 4 is `src/medomni/perception/registry/torch.yaml`: the CPU build index and the torch versions encoders pin. Images are CPU builds because the GPU build is about 5 GB larger, and the deployment, not the image, decides the device. A host that wants another build, such as CUDA, ships its own `perception/torch.yaml` in one [plug-in content folder](../core/plugins.md), which replaces the list. Two content folders that ship one are refused.

Stages 5 and 6 run the encoder's tests in `tests/perception/`. `--freeze` records `expected.json` from the current build; a later change that alters the responses fails stage 5.

`--record` writes an encoder that passed into `perception/deployed.yaml`, which pins the image the perception service starts for each encoder. It refuses an image built from uncommitted source, and leaves the other encoders' entries as they are, except that it drops an entry whose encoder has no folder in the repository or any plug-in content folder. The service serves an encoder whose entry passed stage 5 and did not fail stage 6. `--record` and `--freeze` can't be combined.

## Images

- One image per encoder, built on your machine by `medomni perception check`, tagged `ghcr.io/medomni/<encoder>:dev`. MedOmni doesn't publish encoder images yet, so `medomni perception pull` has nothing to pull.
- In a Bench run, the perception service starts only the image `perception/deployed.yaml` records for an encoder, by content id. Record your build with `--record`, then build the service image, which carries the record.
- Users run images; they never install encoder code.
- Licenses differ; the [Encoders reference](../../reference/encoders.md) lists each one.

## Where it lives

- `perception/encoders/<family>/<encoder>/`: each encoder
- `src/medomni/perception/runtime/`: the serving code shared by every image, with one decoder per family in `decoders/`
- `src/medomni/perception/registry/`: the catalogue, image builds and pulls, and `torch.yaml`, the torch builds an image may install
- `perception/deployed.yaml`: the images the perception service starts, written by `--record`
- `tests/perception/`: the encoder tests the check runs

## Where next

- [Encoders reference](../../reference/encoders.md): model card fields and every encoder in this version.
- [Gateway](gateway.md): how encoders are found and called.
- [Families](../core/families.md): what an encoder reads.
