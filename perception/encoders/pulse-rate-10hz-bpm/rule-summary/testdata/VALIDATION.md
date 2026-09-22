# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[pulse-rate-10hz-bpm__rule-summary] ok — 5 real family sample(s), offline
Pinned revision: e7c52128e841cabf495eed4b3d01ea7808a06e9b

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

Image: ghcr.io/medomni/pulse-rate-10hz-bpm__rule-summary:dev

Synthetic fixture SHA-256:

{
  "input-empty.edf": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.edf": "361e206330b48c7b5447c8db8a4027a483c76d518a3649b7c3c99c9742bb2ab7"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
