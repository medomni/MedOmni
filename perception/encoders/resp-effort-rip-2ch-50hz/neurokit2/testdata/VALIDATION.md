# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input.edf`.
- Rejected inputs: `input-flat.edf`.
- All output labels match the card. All numeric outputs are finite.

Run from the repository root after the asset preparation and build commands in `demo.py`:

```sh
uv run --with jsonschema perception/registry.py validate resp-effort-rip-2ch-50hz__neurokit2
uv run perception/registry.py test resp-effort-rip-2ch-50hz__neurokit2 --docker
docker run --rm --network none ghcr.io/medomni/resp-effort-rip-2ch-50hz__neurokit2:dev python serve.py encode --family resp-effort-rip-2ch-50hz --path input.edf --data-root /app/testdata
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.
