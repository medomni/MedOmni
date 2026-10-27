# Run your agent

This guide is for model testers: you end up with your own model scored on MedOmni atom tasks, with and without encoders.

## Before you start

- The first experiment in [Get started](../get-started.md) working.
- Atom tasks built for the task types you want, in each variant you want to compare. Build the `noenc` arm with `--variant noenc`; it lands in `data_task/atomtasks-noenc/`.
- An API key for your model in the keys file named by `harness/config.yaml`.

## Steps

1. Add an agent config. Copy an existing one and change the model. Keys travel only as `${VARNAME}` references to the keys file, never as values.

    ```bash
    cp harness/harbor/agents/terminus-2-sol.yaml harness/harbor/agents/terminus-2-mymodel.yaml
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

2. Probe the model and note the name the provider reports back. A requested alias is not proof of what answered: `deepseek-chat` is served as `deepseek-flash`. Record the model in `harness/models.yaml` with that served name.
3. Declare the experiment: your agent, both arms, and the repetitions. Each agent × variant × repetition becomes one Harbor job.

    ```yaml
    experiment: my-model-v1
    tier: SMOKE
    description: my model, encoder vs no-encoder arm
    generation: fix-smoke
    types: all
    variants: {enc: data_task/atomtasks, noenc: data_task/atomtasks-noenc}
    agents: [terminus-2-mymodel]
    reps: [1, 2]
    concurrency: 4
    expect: {terminus-2-mymodel: {model_served: my-model-2026-10-01}}
    ```

4. Emit, sign each prerun sheet, and run each job's `harbor run` command, as in [Get started](../get-started.md).

    ```bash
    python harness/build.py emit my-model-v1
    ```

5. Import every job, then score and tabulate.

    ```bash
    python harness/build.py import runs/experiments/my-model-v1/jobs/<job>
    ```

    ```bash
    python harness/score.py --experiment my-model-v1
    ```

    ```bash
    python harness/analyze.py grid my-model-v1
    ```

## Check

`python harness/build.py status my-model-v1` shows which atoms of each cell are present. The scorer refuses a cell, rather than scoring it, when a cohort subject is missing, when its runs disagree on fingerprint or served model, or when the verifier crashes. Agent failures are real results: they count as chance for AUC targets. Infrastructure failures refuse the cell.

The grid in `runs/experiments/my-model-v1/analysis/grid.md` shows task × model × variant, with atom counts, failure rate, cost and encoder use.

## Where next

- [Ledger row](../learn/contracts/ledger-row.md): what each run and score records.
- [Use the encoders](use-the-encoders.md): what the encoder arm gives your agent.
- [Constitution](../learn/constitution.md): the rules on scoring and evidence.
