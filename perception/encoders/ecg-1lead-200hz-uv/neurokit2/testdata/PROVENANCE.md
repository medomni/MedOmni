# Published test data

Source: [MIT-BIH Arrhythmia Database 1.0.0](https://physionet.org/content/mitdb/1.0.0/). Moody and Mark, 2001.

License: ODC-By 1.0 (https://opendatacommons.org/licenses/by/1-0/). Retain attribution and license notices with these excerpts.

Record 100, first 300 seconds, MLII lead. Multiply mV by 1000, then scipy.signal.resample_poly(up=5, down=9). Store EDF at 200 Hz in uV. Reference beat times retain the original 360 Hz time base. The flat fixture is an authored rejection case.

Source SHA-256:

- `100.dat`: `b2ea3c250e56e48f4b7b90697832b8ecd1afa1e0bb31f2dcfea4ed6e1075a639`
- `100.hea`: `60ebc904c7bf3e04d142638d3fd5c903e8dc9f10f1ea3264e07926aa089ee75e`
- `100.atr`: `8d8a5349fb16638ebbf649f1779d12e96d91b736b2aafe59db43719ae583d471`

Fixture SHA-256:

- `input-flat.edf`: `c0524ddc2cb5bf211fd78de443c29f6c17a3f1ecfe27f94a4d4af496cca9443b`
- `input.edf`: `d8844473f9f4bfeb2984d92f082b8a2b15e4733e124154d36e0bd868e8dd541a`
