# Run your agent

For agent evaluators. You score your own agent on a MedOmni task set, with and without encoders.

## Before you start

- [Get started](../get-started.md) working end to end on `medomni-bench/smoke-dummy`.
- The task set built from your data. See [Rebuild a task set](rebuild-a-task-set.md).

## Steps

1. Describe your agent in an agent config, starting from the template:

    ```bash
    medomni bench agent new my-agent
    ```

    ```yaml
    name: my-agent
    scaffold: terminus-2
    model: openai/my-model
    route: cloud
    model_served: my-model-2026-10-01
    env:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    max_turns: 300
    ```

    | Field | Meaning |
    |---|---|
    | `scaffold` | The Harbor agent that drives the model. |
    | `model` | The model to request. |
    | `route` | `local` for a model served on your machine, `cloud` for a provider's API. |
    | `model_served` | The model name the provider reports back. A requested alias can be served by a different model; a run that reports another name is recorded as an error and never scored. |
    | `env` | Keys, only as `${VARNAME}` references to `keys.env` in your workspace. Never write a key into the config. |

2. Run the agent on a task set, under each arm you want to compare, as many times as you need:

    ```bash
    medomni bench run --agent my-agent.yaml --set medomni-bench/v1 --arm encoders --arm no-perception --reps 2
    ```

    The built-in arms are `encoders` (with encoders), `no-perception` (without), `encoders-required` (must call at least one) and `modality-ladder` (six rungs of input families). A task set lists the arms it is built under. `medomni bench run` checks the route against each dataset policy first, and resumes if run again. [Runs](../learn/bench/runs.md) explains both. While it runs, it prints one line with the number of finished and failed atom tasks; for a detailed live view, run `medomni studio progress <run>` beside it.

3. Score:

    ```bash
    medomni bench score --set medomni-bench/v1 --agent my-agent
    ```

## Check

`medomni bench score` prints the task × target × agent × arm table and writes it to the workspace. Each row has the score, patient count, failure rate, cost and encoder use. [Scoring](../learn/bench/scoring.md#refusals-and-failures) lists when a score is refused.

## Results file

Every run and every score is one result record, one line in `results.jsonl` in your workspace. You need it only to analyse results beyond the table. [Scoring](../learn/bench/scoring.md#results-file) explains how it is written.

Contract: result record, `src/medomni/core/contracts/schemas/result-record.schema.json`.

| Record | One per | Key fields |
|---|---|---|
| Run (`kind: run`) | agent run on one atom task | `run_id`, `task_set` (`<benchmark>/<set>`), `task` (`<template>@<cohort>`), `task_version` (`N.X`), `intelligence` (`kind: agent` and its name), `config_hash`, `model_served`, `error_kind`, `api_cost`; in its `agent` block: `arm`, `arm_variant` (the ladder's rung, `r1` to `r6`), `encoders_served`, `encoder_calls`, `files_opened` |
| Score (`kind: score`) | task × target × agent × arm × repetition | `run_id`, `task_set`, `task_set_hash`, `target`, `config_hash`, `task_version`, `intelligence`, `arm` and `arm_variant` when the runs had them, `n_atoms`, `n_failed`, `metric`, `value`, `flags`, `encoder_use` |

!!! warning "The results file is patient data"
    Run ids name the patients they ran on, so the file falls under each dataset's data use agreement. Keep it in the workspace.

## Where next

- [Use the encoders](use-the-encoders.md): what the `encoders` arm gives your agent.
- [Datasets](../reference/datasets.md): which routes each dataset allows.
