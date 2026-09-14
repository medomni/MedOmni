# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input.edf`.
- Rejected inputs: `input-flat.edf`.
- All output labels match the card. All numeric outputs are finite.

Run from the repository root after the asset preparation and build commands in `demo.py`:

```sh
uv run --with jsonschema perception/registry.py validate ecg-1lead-200hz-uv__neurokit2
uv run perception/registry.py test ecg-1lead-200hz-uv__neurokit2 --docker
docker run --rm --network none ghcr.io/medomni/ecg-1lead-200hz-uv__neurokit2:dev python serve.py encode --family ecg-1lead-200hz-uv --path input.edf --data-root /app/testdata
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.

The published MIT-BIH reference contains 371 beats. Detection matched 370 within 100 ms.
Run `python -m pytest perception/tests/test_single_ecg.py` in an environment with the encoder dependencies and pytest.
