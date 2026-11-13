# Verification

Verified locally on Linux arm64 with Docker networking disabled.

- Healthy inference: `input-background.edf`, `input.edf`.
- Rejected inputs: `input-flat.edf`.
- All output labels match the card. All numeric outputs are finite.

These responses were frozen with v0.2.1's encoder check. v0.3 reads these files as test inputs only.

The frozen results detect changes in this implementation. They do not establish diagnostic accuracy.

`reference-seizures.json` contains the published seizure times, separate from model output.
The dataset has no reference ICA component labels. The 90 Hz filter differs from ICLabel training.
