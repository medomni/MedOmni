# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input.edf`.
- Rejected inputs: `input-flat.edf`.
- All output labels match the card. All numeric outputs are finite.

Check from the repository root: this builds the image and compares the test data with `expected.json`.

```sh
medomni perception check perception/encoders/ecg-1lead-200hz-uv/neurokit2
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.

The published MIT-BIH reference contains 371 beats. Detection matched 370 within 100 ms.
`tests/perception/test_decoders_single_ecg.py` checks it.
