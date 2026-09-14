# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input.hea`.
- Rejected inputs: `input-flat.hea`.
- All output labels match the card. All numeric outputs are finite.

Run from the repository root after the asset preparation and build commands in `demo.py`:

```sh
uv run --with jsonschema perception/registry.py validate abp-waveform-125hz-mmhg__pyvital-hpi
uv run perception/registry.py test abp-waveform-125hz-mmhg__pyvital-hpi --docker
docker run --rm --network none ghcr.io/medomni/abp-waveform-125hz-mmhg__pyvital-hpi:dev python serve.py encode --family abp-waveform-125hz-mmhg --path input.hea --data-root /app/testdata
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.
