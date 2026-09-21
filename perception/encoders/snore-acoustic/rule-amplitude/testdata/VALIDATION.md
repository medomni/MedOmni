# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[snore-acoustic__rule-amplitude] ok — 5 real family sample(s), offline
Pinned revision: 0bd2e9cbc47e3ccc9efa6290ee8abc88c561f29a

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

Image: ghcr.io/medomni/snore-acoustic__rule-amplitude:dev

Synthetic fixture SHA-256:

{
  "input-empty.edf": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.edf": "8099699f6d1d712db426b2adf715b17d9abebc447afca64e4b7c1107ebfc0344"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
