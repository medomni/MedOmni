# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input-normal.jpeg`, `input-pneumonia.jpeg`.
- Rejected inputs: `input-invalid.txt`.
- All output labels match the card. All numeric outputs are finite.

Run from the repository root after the asset preparation and build commands in `demo.py`:

```sh
uv run --with jsonschema perception/registry.py validate cxr-radiograph-2d__biomedclip
uv run perception/registry.py test cxr-radiograph-2d__biomedclip --docker
docker run --rm --network none ghcr.io/medomni/cxr-radiograph-2d__biomedclip:dev python serve.py encode --family cxr-radiograph-2d --path input-normal.jpeg --data-root /app/testdata
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.
