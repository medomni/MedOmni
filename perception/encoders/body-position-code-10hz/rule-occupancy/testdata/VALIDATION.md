# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[body-position-code-10hz__rule-occupancy] ok — 5 real family sample(s), offline
Pinned revision: 6a384311c8e3958d7563f3df8a12ad6fae7e7aa7

{
  "sample-01.edf": {
    "healthy": true,
    "notes": [
      "Device codebook unavailable; no anatomical posture mapping applied."
    ]
  },
  "sample-02.edf": {
    "healthy": true,
    "notes": [
      "Device codebook unavailable; no anatomical posture mapping applied."
    ]
  },
  "sample-03.edf": {
    "healthy": true,
    "notes": [
      "Device codebook unavailable; no anatomical posture mapping applied."
    ]
  },
  "sample-04.edf": {
    "healthy": true,
    "notes": [
      "Device codebook unavailable; no anatomical posture mapping applied."
    ]
  },
  "sample-05.edf": {
    "healthy": true,
    "notes": [
      "Device codebook unavailable; no anatomical posture mapping applied."
    ]
  }
}

Image: ghcr.io/medomni/body-position-code-10hz__rule-occupancy:dev

Synthetic fixture SHA-256:

{
  "input-empty.edf": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.edf": "2a4684802eb4b8861a599f0914afbfe7d8e8d6346e127888f7591ae070d3025a"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
