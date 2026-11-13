# Test your agent

For agent evaluators. You evaluate how your agent performs on MedOmni's medical tasks under the conditions you choose, such as with and without encoders, and read the scores.

## What you can test

A task set fixes the tasks; an arm fixes the conditions the agent works under. A set lists the arms it is built for, and every score row names its arm, so you compare one agent across arms, or several agents under one arm.

| Arm | The agent gets |
|---|---|
| `encoders` | The patient's evidence and the encoders for the families it holds. |
| `no-perception` | The same evidence, with no encoders. |
| `encoders-required` | The evidence and the encoders, and it must call at least one. |
| `modality-ladder` | Six rungs, each adding input families to the last, to show how performance changes as modalities are added. |

| Task set | Holds | Arms |
|---|---|---|
| `medomni-bench/smoke-dummy` | One pair per template, on generated data: checks that the pipeline works. | `encoders` |
| `medomni-bench/v1` | The credentialed templates. | `encoders`, `no-perception` |
| `medomni-bench/vitaldb` | The VitalDB templates, on an open dataset. | `encoders`, `no-perception` |
| `medomni-bench/modality-ladder` | The ladder templates at their ladder cohort. | `modality-ladder` |

[Runs](../learn/bench/runs.md) explains arms, and [Tasks](../reference/tasks.md) the task sets.

## Before you start

- [Get started](../get-started.md) working end to end on `medomni-bench/smoke-dummy`.
- The task set built from your data. See [Rebuild a task set](rebuild-a-task-set.md).

## Steps

1. Describe your agent in an agent config, starting from the template:

    ```bash
    medomni bench agent new my-agent
    ```

    ```yaml
    kind: agent
    name: my-agent
    model: openai/my-model
    route: cloud
    settings:
      scaffold: terminus-2
      model_served: my-model-2026-10-01
      env:
        OPENAI_API_KEY: ${OPENAI_API_KEY}
      max_turns: 300
    ```

    | Field | Meaning |
    |---|---|
    | `kind` | The kind of intelligence: `agent`. |
    | `name` | The agent's name, as records show it. |
    | `model` | The model to request. |
    | `route` | `local` for a model served on your machine, `cloud` for a provider's API. Bench refuses a run on a route a dataset's policy denies, and prints the conditions of a `conditional` route, which you must meet; see [Datasets](../reference/datasets.md#datasets-in-v030). |
    | `runner` | Optional: a runner other than the kind's own. MedOmni's tests use `runner: replay`. |
    | `settings` | What the runner reads. For the agent runner, on Harbor, the fields below; the runner checks them. |
    | `settings.scaffold` | The Harbor agent that drives the model. |
    | `settings.model_served` | The model name the provider reports back. A requested alias can be served by a different model; a run that reports another name is recorded as an error and never scored. |
    | `settings.env` | Keys, only as `${VARNAME}` references to variables you export in the shell that runs `medomni bench run`. Never write a key into the config: on a `cloud` route the runner refuses a key that is not a reference. |
    | `settings.max_turns` | The most turns the agent may take on one atom task. |
    | `settings.api_base` | The provider's base URL, for a model server on your machine or a compatible API. |

2. Export your model provider's key in your shell, then run the agent on a task set, under each arm you want to compare:

    ```bash
    export OPENAI_API_KEY=...
    ```

    ```bash
    medomni bench run --agent my-agent.yaml --set medomni-bench/v1 --arm encoders --arm no-perception
    ```

    Without `--arm`, it runs every arm the set lists. `medomni bench run` first checks the built tasks, and resumes if run again. [Runs](../learn/bench/runs.md) explains both. While it runs, it prints one line with the number of finished and failed atom tasks; for a detailed live view, run `medomni studio progress <run>` beside it.

3. Score:

    ```bash
    medomni bench score --set medomni-bench/v1 --agent my-agent
    ```

## Check

`medomni bench score` prints the task × target × agent × arm table and writes it to the workspace. Each row has the score, patient count, failure rate, cost and encoder use. [Scoring](../learn/bench/scoring.md#refusals-and-failures) lists when a score is refused.

## Results file

Every run and every score is one result record. Run records are lines of `runs.jsonl` in each [run folder](../learn/bench/runs.md#run-folders); score records are lines of `results.jsonl` in your workspace. You need them only to analyse results beyond the table. [Scoring](../learn/bench/scoring.md#results-file) explains how it is written.

Contract: result record, `src/medomni/core/contracts/schemas/result-record.schema.json`.

| Record | One per | Key fields |
|---|---|---|
| Run (`kind: run`) | agent run on one atom task | `run_id`, `task_set` (`<benchmark>/<set>`), `task` (`<template>@<cohort>`), `task_version` (`N.X`), `intelligence` (`kind: agent` and its name), `config_hash`, `model_served`, `error_kind`, `api_cost`; in its `agent` block: `arm`, `arm_variant` (the ladder's rung, `r1` to `r6`), `encoders_served`, `encoder_calls`, `files_opened` |
| Score (`kind: score`) | task × target × agent × arm × repetition | `run_id`, `task_set`, `task_set_hash`, `target`, `config_hash`, `task_version`, `intelligence`, `arm` and `arm_variant` when the runs had them, `n_atoms`, `n_failed`, `metric`, `value`, `flags`, `encoder_use` |

!!! warning "Result records are patient data"
    Run ids name the patients they ran on, so the run folders and the results file fall under each dataset's data use agreement. Keep them in the workspace.

## Where next

- [Use the encoders](use-the-encoders.md): what the `encoders` arm gives your agent.
- [Datasets](../reference/datasets.md): which routes each dataset allows.
