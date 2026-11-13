# Task-check fixtures

Synthetic must-fail cases and their controls for four of Build's task checks, read by `tests/studio/test_checks.py`: **t1-eligible** (an index stay must still be open at the prediction time), **t1-leak** (the index admission row carries no outcome field), **t1-eventgate** (no positive's event falls at or before the prediction time) and **t1-constgold** (gold constant over the pool, or outside plausible bounds).
Expected verdicts per case are in `EXPECTATIONS.yaml`.

## Fenced: never a real atom

- Every value is invented: subject ids `FX0101…`, admission ids `FXH…`, timestamps in 2149–2150, no real row.
- Unrunnable by construction: no `environment/` (Harbor cannot build them), a `FIXTURE_DO_NOT_RUN` sentinel in every atom and parent, `batch = "fixture"`, `generation = "fix-fixture"`, `[metadata] fixture = true`, and an instruction that is only a fence line.

## Shape

Facts only the builder may see are in each case's `parents/<task>__fixture/parent.json`, not in the atom's staged files:

- `index_stay[sid] = {hadm_id, admit, disch, death}`: t1-eligible and t1-leak (which row is the index row);
- `boundaries[sid]`, `event_times[target][sid]`, and `targets[].event = true`: t1-eventgate;
- `pool_stats[target] = {derivation, metric_family, n_eligible, counts}`: t1-constgold (summary counts, not per-subject gold).

## One mutation per case

Each case differs from its gate's `control` by exactly one declared line, checked with `diff -r <gate>/control <gate>/<case>`. t1-constgold cases are standalone pool summaries.
