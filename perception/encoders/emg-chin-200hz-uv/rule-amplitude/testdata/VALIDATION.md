# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[emg-chin-200hz-uv__rule-amplitude] ok — 5 real family sample(s), offline
Pinned revision: 33b3e3e0a2405e6bfa114bfa82e7e307783eddac

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

Image: ghcr.io/medomni/emg-chin-200hz-uv__rule-amplitude:dev

Synthetic fixture SHA-256:

{
  "input-empty.edf": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.edf": "01877e19a9a33298107a5101dd4daba4b8fbf601de0e2a02bae407a28bc93b26"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
