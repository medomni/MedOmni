# Verification

Independent fixture: [60, 80, 100, 0] bpm at one-minute timestamps.
Positive observations have mean/median 80 bpm, count 3; excluded count 1;
observed span 180 seconds. Empty input degrades.

Passed registry validate; Docker build, freeze, rebuild, test (2 fixtures);
baked demo including HTTP 400/404 error probes; family-test with networking
disabled (5/5 healthy, SHA-256 verified).
Real samples: MedOmni/family-samples, revision
44576464d4647cc2cc1347103ca0b09746c26d9f,
families/wearable-hr-1min-bpm/sample-01.json through sample-05.json.
Image: ghcr.io/medomni/wearable-hr-1min-bpm__rule-summary:dev.
Smoke tests do not establish clinical reliability.
