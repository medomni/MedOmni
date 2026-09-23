# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

NA: family declaration has samples: null; no published HF sample.

Image: ghcr.io/medomni/retinal-heightmap-surfaces-f32__rule-surfaces:dev

Synthetic fixture SHA-256:

{
  "input-empty.dcm": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input.dcm": "5108f39bb482f6125150c7c3c8bb3e1c8060c88d22263e2a4463c6b85c3df960"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
