# Scoring

The scorer turns the runs of one task into one score per agent, condition and repetition. It is the only part of MedOmni that writes scores.

```text
runs of one task ──collect predictions──▶ compare with the task's answers ──▶ one score row
```

## How a score is made

1. Collect every atom task's prediction for the task, agent, condition and repetition.
2. Check the set is complete and consistent.
3. Compare the predictions with the task's answers, using the metric in the task spec.
4. Write one score row to the results file.

Scoring a task as a whole, after all its runs finish, means no run sees the answers.

## Refusals and failures

- A task with missing patients is refused.
- A task whose runs differ in fingerprint or served model is refused.
- An agent failure, such as no answer or a malformed answer, scores as chance.
- An infrastructure failure refuses the score.

## Metrics

Each task's spec names one metric: `accuracy`, `auc`, `macro_auc`, `brier`, `qwk` or `mae`. Each score row records the scorer version, a hash of the metric code. `medomni bench score --force` rescores under the current version.

## Results file

`results.jsonl` in your workspace holds every run and every score, one line each.

- Only `medomni bench run` and `medomni bench score` write it.
- Lines are never edited; for a repeated `run_id`, the latest line wins.

## Where it lives

- `bench/scoring/`: the scorer and the metrics
- your workspace: `results.jsonl`

## Where next

- [Run your agent](../../guides/run-your-agent.md#results-file): the results file fields.
- [Tasks](tasks.md): where the metric and answers come from.
