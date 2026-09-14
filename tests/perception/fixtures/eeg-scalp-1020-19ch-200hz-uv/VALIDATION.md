# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input-background.edf`, `input.edf`.
- Rejected inputs: `input-flat.edf`.
- All output labels match the card. All numeric outputs are finite.

Run from the repository root after the asset preparation and build commands in `demo.py`:

```sh
uv run --with jsonschema perception/registry.py validate eeg-scalp-1020-19ch-200hz-uv__iclabel
uv run perception/registry.py test eeg-scalp-1020-19ch-200hz-uv__iclabel --docker
docker run --rm --network none ghcr.io/medomni/eeg-scalp-1020-19ch-200hz-uv__iclabel:dev python serve.py encode --family eeg-scalp-1020-19ch-200hz-uv --path input-background.edf --data-root /app/testdata
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.

`reference-seizures.json` contains the published seizure times, separate from model output.
The dataset has no reference ICA component labels. The 90 Hz filter differs from ICLabel training.
