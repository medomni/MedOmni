# Published test data

Source: [Apnea-ECG 1.0.0](https://physionet.org/content/apnea-ecg/1.0.0/). Penzel et al., Computers in Cardiology 2000.

License: ODC-By 1.0 (https://opendatacommons.org/licenses/by/1-0/). Retain attribution and license notices with these excerpts.

Record a01r, seconds [510,810). Select Resp C and Resp A. Apply scipy.signal.resample_poly(up=1, down=2) from 100 to 50 Hz. Rename channels thorax and abdomen. Amplitude remains uncalibrated. The flat fixture is an authored rejection case.

Source SHA-256:

- `a01.apn`: `b7404271c576572ce8c99af1fe455cae2954dce1c18caf21a61a25bf1c00f803`
- `a01r.hea`: `9cb44adf30f78742cdc34027e59dd8b316a079938f2b8c0ae2d703582bd18571`
- `a01r.dat`: `368612afa4c755a240e6e66c77ec9957a07ac98c9f4560784d999c64d8302d0d`

Fixture SHA-256:

- `input-flat.edf`: `82f17d2d5396f93d36d02b984c0fd53776a753feb520ef473cab1304c3bef498`
- `input.edf`: `ab986398399d632a04e60bd49c1bb7ee39ad23ac238df0d233cfb843c20c195d`
