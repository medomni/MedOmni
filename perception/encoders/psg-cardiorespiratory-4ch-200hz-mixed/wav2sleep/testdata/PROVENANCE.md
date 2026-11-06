# Test-data provenance

`input.edf` is generated: 300 seconds of ECG, pleth and the abdominal and thoracic belts at 200 Hz, all from one subject, from MedOmni's dummy-data generator at the physiology level. It holds no recorded data.

Regenerate it from the repository root:

```bash
uv run python -c "from medomni.core import families; from medomni.core.families.dummy import make_dummy; make_dummy(families.get('psg-cardiorespiratory-4ch-200hz-mixed'), seed=2026, out_dir='perception/encoders/psg-cardiorespiratory-4ch-200hz-mixed/wav2sleep/testdata', name='input', subject='DUMMY-1')"
```

- Generator: `medomni.core.families.dummy`, MedOmni 0.3.0.dev0, seed 2026, subject `DUMMY-1`.
- License: the repository's license.
- `expected.json` was produced from an earlier input and is regenerated when the encoder image runs on this file (Stage 3, T2).
