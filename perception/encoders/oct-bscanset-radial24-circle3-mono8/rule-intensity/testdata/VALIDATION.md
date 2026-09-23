# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[oct-bscanset-radial24-circle3-mono8__rule-intensity] ok — 3 real family sample(s), offline
Pinned revision: 44576464d4647cc2cc1347103ca0b09746c26d9f

{
  "sample-01.dcm": {
    "healthy": true,
    "notes": [
      "Stored pixel intensities; no spatial resampling, modality LUT or physical calibration."
    ]
  },
  "sample-02.dcm": {
    "healthy": true,
    "notes": [
      "Stored pixel intensities; no spatial resampling, modality LUT or physical calibration."
    ]
  },
  "sample-03.dcm": {
    "healthy": true,
    "notes": [
      "Stored pixel intensities; no spatial resampling, modality LUT or physical calibration."
    ]
  }
}

Image: ghcr.io/medomni/oct-bscanset-radial24-circle3-mono8__rule-intensity:dev

Synthetic fixture SHA-256:

{
  "input-empty.dcm": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.dcm": "f5bc3ec35996561811894c82a458725298bc20eed4ae2156162e9e7bb5da319b"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
