# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[emg-limb-200hz-uv__rule-amplitude] ok — 5 real family sample(s), offline
Pinned revision: 44576464d4647cc2cc1347103ca0b09746c26d9f

{
  "sample-01.edf": {
    "healthy": true,
    "notes": [
      "Right Leg read as leg-right",
      "Right Arm read as arm-right",
      "Left Arm read as arm-left",
      "Left Leg read as leg-left"
    ]
  },
  "sample-02.edf": {
    "healthy": true,
    "notes": [
      "Right Leg read as leg-right",
      "Right Arm read as arm-right",
      "Left Arm read as arm-left",
      "Left Leg read as leg-left"
    ]
  },
  "sample-03.edf": {
    "healthy": true,
    "notes": [
      "Leg 1 read as leg-left",
      "Leg 2 read as leg-right"
    ]
  },
  "sample-04.edf": {
    "healthy": true,
    "notes": [
      "Leg 1 read as leg-left",
      "Leg 2 read as leg-right"
    ]
  },
  "sample-05.edf": {
    "healthy": true,
    "notes": [
      "Leg 1 read as leg-left",
      "Leg 2 read as leg-right"
    ]
  }
}

Image: ghcr.io/medomni/emg-limb-200hz-uv__rule-amplitude:dev

Synthetic fixture SHA-256:

{
  "input-empty.edf": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.edf": "c11b1aef37468567acc9ca98818a2dcea27e2e9b3a8e9cd869bf5f7060801c7c"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
