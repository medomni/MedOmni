# Test-data provenance

`input.edf` is generated: 300 seconds of the two EOG channels (`e1-m2`, `e2-m1`) at 200 Hz, from MedOmni's dummy-data generator at the physiology level. It holds no recorded data.

Regenerate it from the repository root:

```bash
uv run python -c "from medomni.core import families; from medomni.core.families.dummy import make_dummy; make_dummy(families.get('eog-2ch-200hz-uv'), seed=2026, out_dir='perception/encoders/eog-2ch-200hz-uv/wav2sleep-eog/testdata', name='input', subject='DUMMY-1')"
```

- Generator: `medomni.core.families.dummy`, MedOmni 0.3.0.dev0, seed 2026, subject `DUMMY-1`.
- License: the repository's license.
- `expected.json` is the encoder image's response to this file (Stage 3, T2); v0.2.1's image gives the same response.
