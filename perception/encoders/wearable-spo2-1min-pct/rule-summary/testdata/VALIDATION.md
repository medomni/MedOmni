# Verification

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild, regression test, and baked demo PASS (including HTTP 400/404 error probes). Real-sample family-test runs with Docker networking disabled and verifies manifest SHA-256 hashes.

[wearable-spo2-1min-pct__rule-summary] REJECTED: RuntimeError: sample-01.json: real family sample did not produce healthy output; sample-01.json: card declares 1 output block(s), got 0; sample-02.json: real family sample did not produce healthy output; sample-02.json: card declares 1 output block(s), got 0; sample-03.json: real family sample did not produce healthy output; sample-03.json: card declares 1 output block(s), got 0; sample-04.json: real family sample did not produce healthy output; sample-04.json: card declares 1 output block(s), got 0
Pinned revision: 44576464d4647cc2cc1347103ca0b09746c26d9f

{
  "sample-01.json": {
    "healthy": false,
    "notes": [
      "cannot read wearable OMH: no measurements"
    ]
  },
  "sample-02.json": {
    "healthy": false,
    "notes": [
      "cannot read wearable OMH: no measurements"
    ]
  },
  "sample-03.json": {
    "healthy": false,
    "notes": [
      "cannot read wearable OMH: no measurements"
    ]
  },
  "sample-04.json": {
    "healthy": false,
    "notes": [
      "cannot read wearable OMH: no measurements"
    ]
  },
  "sample-05.json": {
    "healthy": false,
    "notes": [
      "cannot read wearable OMH: no measurements"
    ]
  }
}

Image: ghcr.io/medomni/wearable-spo2-1min-pct__rule-summary:dev

Synthetic fixture SHA-256:

{
  "input-empty.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
  "input.json": "e9132c8151ff4c270548a7e769e713dac503153ba698d077b4264c040e1394ea"
}

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Synthetic fixtures are Apache-2.0. Smoke tests do not establish clinical reliability.
