# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input-normal.jpeg`, `input-pneumonia.jpeg`.
- Rejected inputs: `input-invalid.txt`.
- All output labels match the card. All numeric outputs are finite.

Check from the repository root: this builds the image and compares the test data with `expected.json`.

```sh
medomni perception check perception/encoders/cxr-radiograph-2d/biomedclip
```

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.
