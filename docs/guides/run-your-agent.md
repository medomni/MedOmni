# Run your agent

This guide is for agent evaluators: you end up with your own model scored on MedOmni, with and without encoders.

## Before you start

- [Get started](../get-started.md) working end to end.
- Atom tasks built for each condition you compare. Build the no-encoder ones with `--variant noenc`; they land in `data_task/atomtasks-noenc/`.

## Steps

1. Add an agent config by copying an existing one and changing the model. Keys appear only as `${VARNAME}` references to your keys file.

    ```bash
    cp harness/harbor/agents/terminus-2-gpt.yaml harness/harbor/agents/terminus-2-mymodel.yaml
    ```

    ```yaml
    agents:
      - name: terminus-2
        model_name: openai/my-model
        env:
          OPENAI_API_KEY: ${OPENAI_API_KEY}
        kwargs:
          max_turns: 300
    ```

2. Send the model one request and note the model name the provider reports back. A requested alias can be served by a different model, so record the served name in `harness/models.yaml` and in the experiment's `expect`.
3. Declare the experiment. Each agent × condition × repetition becomes one Harbor job.

    ```yaml
    experiment: my-model-v1
    tier: SMOKE
    description: my model, with and without encoders
    generation: fix-smoke
    types: all
    variants: {enc: data_task/atomtasks, noenc: data_task/atomtasks-noenc}
    agents: [terminus-2-mymodel]
    reps: [1, 2]
    concurrency: 4
    expect: {terminus-2-mymodel: {model_served: my-model-2026-10-01}}
    ```

4. Emit, run each job's `harbor run` command and import each job, as in [Get started](../get-started.md).

    ```bash
    python harness/build.py emit my-model-v1
    ```

    ```bash
    python harness/build.py status my-model-v1
    ```

    `status` shows which patients of each task type have a run, so you know when the experiment is complete.

5. Score and tabulate.

    ```bash
    python harness/score.py --experiment my-model-v1
    ```

    ```bash
    python harness/analyze.py grid my-model-v1
    ```

## Check

`runs/experiments/my-model-v1/analysis/grid.md` shows task × agent × condition, with patient counts, failure rate, cost and encoder use. A task type with missing patients, or with runs that disagree on fingerprint or served model, is refused rather than scored. An agent's failure scores as chance; an infrastructure failure refuses the score.

## Results file

Every run and every score is one line in `runs/ledger/results.jsonl`, written only by `build.py import` and `score.py`. You need it only to analyse results beyond the grid. Lines are never edited; for a repeated `run_id`, the latest line wins.

| Record | One per | Key fields |
|---|---|---|
| Run (`kind: atom`) | agent run on one atom task | `run_id`, `task`, `agent`, `variant`, `fingerprint`, `model_served`, `encoder_calls`, `files_opened`, `error_kind`, `api_cost` |
| Score (`kind: cell`) | task type × agent × condition × repetition | `run_id`, `fingerprint`, `n_atoms`, `n_failed`, `metric`, `value`, `flags`, `encoder_use` |

!!! warning "The results file is patient data"
    Run ids contain the dataset's subject ids, so the file falls under each dataset's data use agreement. Keep it under `runs/`, which git ignores.

## Where next

- [Use the encoders](use-the-encoders.md): what the encoder condition gives your agent.
