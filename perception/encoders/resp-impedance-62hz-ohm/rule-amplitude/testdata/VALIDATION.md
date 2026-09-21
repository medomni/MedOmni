# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[resp-impedance-62hz-ohm__rule-amplitude] ok — 5 real family sample(s), offline
Pinned revision: 44576464d4647cc2cc1347103ca0b09746c26d9f

{
  "sample-01.hea": {
    "healthy": true,
    "notes": []
  },
  "sample-02.hea": {
    "healthy": true,
    "notes": []
  },
  "sample-03.hea": {
    "healthy": true,
    "notes": []
  },
  "sample-04.hea": {
    "healthy": true,
    "notes": []
  },
  "sample-05.hea": {
    "healthy": true,
    "notes": []
  }
}

Image: ghcr.io/medomni/resp-impedance-62hz-ohm__rule-amplitude:dev

Synthetic fixture SHA-256:

{
  "input-empty.hea": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.hea": "5131bc96133eaf179a169dfc465fa077e9b8017b1255e3754539acbf5d5f767e"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
