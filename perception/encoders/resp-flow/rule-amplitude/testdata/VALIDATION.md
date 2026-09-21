# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[resp-flow__rule-amplitude] ok — 5 real family sample(s), offline
Pinned revision: 16ffcea165fa30f6796d9b9f1dabfeb8407e6127

{
  "sample-01.edf": {
    "healthy": true,
    "notes": []
  },
  "sample-02.edf": {
    "healthy": true,
    "notes": []
  },
  "sample-03.edf": {
    "healthy": true,
    "notes": []
  },
  "sample-04.edf": {
    "healthy": true,
    "notes": []
  },
  "sample-05.edf": {
    "healthy": true,
    "notes": []
  }
}

Image: ghcr.io/medomni/resp-flow__rule-amplitude:dev

Synthetic fixture SHA-256:

{
  "input-empty.edf": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.edf": "c8fe6b6601efdd3944afc9a6ce0927659e4ba4cd0c5337f88cfa266d0e20fd09"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
