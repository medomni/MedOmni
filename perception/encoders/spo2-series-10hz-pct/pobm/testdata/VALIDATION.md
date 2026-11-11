# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input.edf`.
- Rejected inputs: `input-zero.edf`.
- All output labels match the card. All numeric outputs are finite.

Check from the repository root: this builds the image and compares the test data with `expected.json`.

```sh
medomni perception check perception/encoders/spo2-series-10hz-pct/pobm
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.
