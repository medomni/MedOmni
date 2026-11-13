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

## Metrics

Each target in a template names its metric, a name registered in `medomni.metrics`. Bench registers three:

- `auc`: binary targets
- `qwk`: ordinal targets
- `mae`: numeric targets

Each score record holds the scorer version, a hash of the metric code. `medomni bench score --force` rescores under the current version.

## Behaviour metrics

On an arm with the perception service, Bench measures how far the agent took each encoder answer, at three levels:

- **called**: the call is in the perception service's call log
- **surfaced**: a value from the answer appears in the agent's terminal output after the call
- **cited**: a message from the agent names that value before it writes its answer

Whether an answer changed the prediction needs a paired run without it, so that level is reported as unmeasured. Every encoder counts, whether or not its family bears on the targets.

- Each run record counts the agent's calls per encoder, in `agent.encoder_calls`.
- The run folder's `encoder_use.jsonl` holds each call's level.
- Each score record's `encoder_use` sums up its row: how many atom tasks called an encoder, the share that reached each level, over those atom tasks and over all of them, and the share of surfaced answers never cited.

## Stand-in agents

Before every run, `medomni bench run` scores two stand-in agents on each task, with no model calls:

- one that answers every patient's true values must score perfectly: AUC 1, QWK 1, MAE 0
- one that gives every patient the same answer, the best one without looking, must score at chance: AUC 0.5, QWK 0, and MAE equal to the answers' mean distance from their median

A task that fails either has broken answers or scoring, such as an answer for no atom task, and nothing runs. The problems name the task, target and both scores, never a patient's value.

## Results file

`results.jsonl` in your workspace holds the score records (`kind: score`). The run records (`kind: run`) stay in each [run folder](runs.md#run-folders)'s `runs.jsonl`.

- Only `medomni bench score` writes it.
- Lines are never edited; for a repeated `run_id`, the latest line wins.

## Where it lives

- `src/medomni/bench/scoring/`: the scorer, the behaviour metrics and the stand-in agents
- `src/medomni/bench/metrics.py`: `auc`, `qwk` and `mae`
- your workspace: `results.jsonl`

## Where next

- [Run your agent](../../guides/run-your-agent.md#results-file): the results file fields.
- [Tasks](../studio/tasks.md): where the metrics and answers come from.
