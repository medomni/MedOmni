# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[flio-tcspc-256x256x1024bin-u16__rule-photons] ok — 3 real family sample(s), offline
Pinned revision: 44576464d4647cc2cc1347103ca0b09746c26d9f

{
  "sample-01.dcm": {
    "healthy": true,
    "notes": [
      "One wavelength-band acquisition; frame axis retained as temporal bins.",
      "Raw arrival-bin moments; no background subtraction, instrument-response correction or lifetime fitting."
    ]
  },
  "sample-02.dcm": {
    "healthy": true,
    "notes": [
      "One wavelength-band acquisition; frame axis retained as temporal bins.",
      "Raw arrival-bin moments; no background subtraction, instrument-response correction or lifetime fitting."
    ]
  },
  "sample-03.dcm": {
    "healthy": true,
    "notes": [
      "One wavelength-band acquisition; frame axis retained as temporal bins.",
      "Raw arrival-bin moments; no background subtraction, instrument-response correction or lifetime fitting."
    ]
  }
}

Image: ghcr.io/medomni/flio-tcspc-256x256x1024bin-u16__rule-photons:dev

Synthetic fixture SHA-256:

{
  "input-empty.dcm": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.dcm": "dbc1156ba9c1877440589a28c1ac03110940b46e675f85856da6925f3c0e031b"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
