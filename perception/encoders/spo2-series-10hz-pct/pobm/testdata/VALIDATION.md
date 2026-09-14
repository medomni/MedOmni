# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input.edf`.
- Rejected inputs: `input-zero.edf`.
- All output labels match the card. All numeric outputs are finite.

Run from the repository root after the asset preparation and build commands in `demo.py`:

```sh
uv run --with jsonschema perception/registry.py validate spo2-series-10hz-pct__pobm
uv run perception/registry.py test spo2-series-10hz-pct__pobm --docker
docker run --rm --network none ghcr.io/medomni/spo2-series-10hz-pct__pobm:dev python serve.py encode --family spo2-series-10hz-pct --path input.edf --data-root /app/testdata
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.
