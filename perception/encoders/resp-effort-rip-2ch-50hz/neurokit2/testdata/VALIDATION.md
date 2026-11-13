# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input.edf`.
- Rejected inputs: `input-flat.edf`.
- All output labels match the card. All numeric outputs are finite.

Check from the repository root: this builds the image and compares the test data with `expected.json`.

```sh
medomni perception check perception/encoders/resp-effort-rip-2ch-50hz/neurokit2
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.
