# Run your agent

This guide is for model testers and practitioners: you end up with your own agent scored on a MedOmni batch.

!!! note "Draft"
    The `medomni` command and the agent template arrive in v1.0.0 (roadmap phases 3 and 4).

## Before you start

- MedOmni installed and the dummy run in [Get started](../get-started.md) working.
- Your agent: a model and a scaffold. MedOmni runs agents through Harbor, so any Harbor-compatible agent works; the default scaffold is `terminus-2`.
- A route for the model. The default is a local open model. A cloud route is allowed only where the dataset policy permits it (see [Datasets](../catalog/datasets.md)).

## Steps

1. Copy the agent template.

    ```bash
    cp templates/agent/local.yaml my-agent.yaml
    ```

2. Edit `my-agent.yaml`: set the model, the scaffold and the route. Name the route (for example `local` or a named cloud service); do not put keys in the file.
3. Run it on the dummy batch first.

    ```bash
    medomni run --agent my-agent.yaml --batch smoke-dummy
    ```

4. Run it on a real batch. MedOmni refuses a run whose route the batch's dataset policy does not allow.

    ```bash
    medomni run --agent my-agent.yaml --batch v1-mini
    ```

5. Score the batch.

    ```bash
    medomni score --batch v1-mini
    ```

## Check

`medomni score` writes one cell row per task and prints the table. Each score cites the batch and the task fingerprints it ran on. A single run is never a result: compare against the batch's baseline and report the campaign, not one run.

## Where next

- [Connect your data](connect-your-data.md): build the credentialed batches from your own access.
- [Use the encoders](use-the-encoders.md): what the encoders give your agent.
- [Ledger row](../learn/contracts/ledger-row.md): what each run and score records.
