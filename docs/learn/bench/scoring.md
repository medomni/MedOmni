# Scoring

The scorer turns the runs of one task into scores: one per target, for each agent, condition and repetition. It is the only part of MedOmni that writes scores.

```text
runs of one task ──collect predictions──▶ compare with the task's answers ──▶ one score row per target
```

## How a score is made

1. Collect every atom task's prediction for the task, agent, condition and repetition.
2. Check the set is complete and consistent.
3. For each target, compare the predictions with the answers, using that target's metric.
4. Write one score row per target to the results file.

Scoring a task as a whole, after all its runs finish, means no run sees the answers.

## Refusals and failures

- A task with missing patients is refused.
- A task whose runs differ in fingerprint or served model is refused.
- An agent failure, such as no answer or a malformed answer, scores as chance.
- An infrastructure failure refuses the score.
- A target whose answers have one class only is unscorable. Its row says so and carries no value.

## Metrics

Each target in a spec names its metric:

- `auc`: binary targets
- `qwk`: ordinal targets
- `mae`: numeric targets

Each score row records the scorer version, a hash of the metric code. `medomni bench score --force` rescores under the current version.

## Behaviour metrics

Next to the score, each run row records how the agent worked:

- encoder use, per call, at three levels:
    - **called**: the call is in the sidecar's call log
    - **surfaced**: a value from the reply appears in the agent's terminal output
    - **cited**: the agent's reasoning names that value before it writes its answer
- whether each called encoder is relevant to the task's targets
- which staged files it opened

## Results file

`results.jsonl` in your workspace holds every run and every score, one line each.

- Only `medomni bench run` and `medomni bench score` write it.
- Lines are never edited; for a repeated `run_id`, the latest line wins.

## Where it lives

- `src/medomni/bench/scoring/`: the scorer, the metrics and the behaviour metrics
- your workspace: `results.jsonl`

## Where next

- [Run your agent](../../guides/run-your-agent.md#results-file): the results file fields.
- [Tasks](tasks.md): where the metrics and answers come from.
