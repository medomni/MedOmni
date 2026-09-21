# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[octa-enface-slab-mono8-2d__rule-intensity] ok — 5 real family sample(s), offline
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
  },
  "sample-04.dcm": {
    "healthy": true,
    "notes": [
      "Stored pixel intensities; no spatial resampling, modality LUT or physical calibration."
    ]
  },
  "sample-05.dcm": {
    "healthy": true,
    "notes": [
      "Stored pixel intensities; no spatial resampling, modality LUT or physical calibration."
    ]
  }
}

Image: ghcr.io/medomni/octa-enface-slab-mono8-2d__rule-intensity:dev

Synthetic fixture SHA-256:

{
  "input-empty.dcm": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.dcm": "3a0d4e018ca6e0091451e9ce0ac934b0836644e4fd6e41eb28542832564872eb"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
