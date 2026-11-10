# Scoring

The scorer turns the runs of one built `<template>@<cohort>` into scores: one per target, for each agent, [arm](runs.md#arms) and repetition. A score record names its arm in `arm`, and the ladder's rung in `arm_variant`. It is the only part of MedOmni that writes scores.

```text
prediction records of one <template>@<cohort> ──▶ compare with its answers ──▶ one score record per target
```

## How a score is made

1. Read the [prediction records](runs.md#prediction-records) of every atom task for the `<template>@<cohort>`, agent, arm and repetition. The scorer reads nothing else from a run.
2. Check the set is complete and consistent.
3. For each target, compare the predictions with the answers, using that target's metric.
4. Write one score record per target to the results file.

Scoring all atom tasks together, after all their runs finish, means no run sees the answers.

## Refusals and failures

- A `<template>@<cohort>` with missing patients is refused.
- Runs that differ among themselves in config hash, served model or served encoders are refused.
- Rows with different config hashes in one table are flagged **configured differently**. The flag never voids a score.
- Each score record carries the task set's content hash. The table only puts scores with the same hash side by side.
- An agent failure, such as no answer or a malformed answer, scores as chance.
- An infrastructure failure refuses the score.

## Checks before any run

`medomni bench task check` scores two stand-in agents on every `<template>@<cohort>`, with no model calls:

- **True answers:** an agent that submits the answers must score perfectly. If not, the answers, the patient order or the metric are wrong.
- **Same answer:** an agent that always gives the same answer must score at chance, skill about 0. If not, the score itself carries information.

Either failure stops the check.

## Metrics

Each target in a template names its metric, a name registered in `medomni.metrics`. Bench registers three:

- `auc`: binary targets
- `qwk`: ordinal targets
- `mae`: numeric targets

Each score record holds the scorer version, a hash of the metric code. `medomni bench score --force` rescores under the current version.

## Behaviour metrics

Next to the score, each run record holds how the agent worked:

- encoder use, per call, at three levels:
    - **called**: the call is in the perception service's call log
    - **surfaced**: a value from the reply appears in the agent's terminal output
    - **cited**: the agent's reasoning names that value before it writes its answer
- whether each called encoder is relevant to the targets
- which staged files it opened

## Results file

`results.jsonl` in your workspace holds the score records (`kind: score`). The run records (`kind: run`) stay in each [run folder](runs.md#run-folders)'s `runs.jsonl`.

- Only `medomni bench score` writes it.
- Lines are never edited; for a repeated `run_id`, the latest line wins.

## Where it lives

- `src/medomni/bench/scoring/`: the scorer and the behaviour metrics
- `src/medomni/bench/metrics.py`: `auc`, `qwk` and `mae`
- your workspace: `results.jsonl`

## Where next

- [Run your agent](../../guides/run-your-agent.md#results-file): the results file fields.
- [Tasks](tasks.md): where the metrics and answers come from.
