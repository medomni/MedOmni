# Fixtures

The fixtures contain the first 60 seconds of the PLETH channel from BIDMC record 01, version 1.0.0.
The native sample rate is 125 Hz. The source physical samples were written to WFDB and EDF with 16-bit quantization.
No patient identifiers or unrelated channels were copied. Both formats describe the same waveform:
`input.hea` with `bidmc.dat` is the WFDB form, `input.edf` the EDF form.

Source: https://physionet.org/content/bidmc/1.0.0/
Authors: Marco Pimentel, Alistair Johnson, Peter Charlton, and David Clifton.
License: Open Data Commons Attribution 1.0; see LICENSE-BIDMC.
Publication: Pimentel et al., Towards a Robust Estimation of Respiratory Rate from Pulse Oximeters, DOI 10.1109/TBME.2016.2613124.
The frozen pulse metrics test reproducibility, not diagnostic accuracy.

Source hashes:
- `bidmc01.hea`: `f43b0b139ad8f4d45097403b7179e1e6f8bda17dfd06dba504faf39a115aa27f`
- `bidmc01.dat`: `b1666c7f2f117be6dc04cae2e7016b3315775edb9ad7c7ee53fa9c110937560b`

## Bad-input fixture

`input-bad-truncated.edf` — The first 2048 bytes of `input.edf`, derived from BIDMC (PhysioNet, ODC-By 1.0; see above). Header only, shorter than the thirty seconds the encoder requires. The EDF patient and recording fields remain 'X X X X'.
