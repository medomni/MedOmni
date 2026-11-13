# Verification (2026-09-23)

Independent verify.py oracle PASS. Registry validate, Docker build, freeze, rebuild and regression test PASS.

Real-sample family-test, Docker networking disabled, manifest SHA-256 verified:

[pressure-nonarterial-125hz-mmhg__rule-summary] ok — 5 real family sample(s), offline
Pinned revision: 123d9ca78103450717a58402d3ab4aadf2428a2e

| Sample | Role | Median (mmHg) | implausible_fraction | Note |
|---|---|---|---|---|
| sample-01 | CVP | 397.9 | 1.00 | flagged: unzeroed transducer pattern |
| sample-02 | CVP | 3.6 | 0.00 | |
| sample-03 | PAP | 20.4 | 0.00 | |
| sample-04 | CVP | 246.3 | 1.00 | flagged: unzeroed transducer pattern |
| sample-05 | CVP | 15.1 | 0.00 | |

Samples 01 and 04 are artifacts in the published family samples, not encoder errors; the family samples should be re-cut with a plausibility screen.

A raw bedside segment from the MIMIC-IV Waveform Database 0.1.0 (open access, ODbL 1.0) (7 channels, pressures at two samples per frame): healthy, CVP and PAP read at 124.945 Hz for 3237 s, five non-pressure channels ignored and reported, 42% (CVP) and 85% (PAP) of samples flagged implausible.

Real samples remain outside Git: redistribution license is unspecified in the HF manifest. Smoke tests do not establish clinical reliability.
