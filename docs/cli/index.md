# CLI

The `medomni` command is the one entrance to MedOmni, with one section per subcommand below.

!!! note "Draft"
    The CLI arrives in v1.0.0 (roadmap phase 3). Each command wraps scripts that exist today, with the same code underneath; flags may still change.

## medomni run

Runs an agent on a batch: builds the job, runs every atom task in Harbor, and imports the results into the ledger.

```bash
medomni run --agent my-agent.yaml --batch v1-mini
```

Checks the agent's route against each dataset policy before it starts. Wraps `harness/build.py emit`, `harbor run` and `harness/build.py import`.

## medomni score

Scores the runs of a batch or experiment: one cell row per task in the ledger, and a summary table.

```bash
medomni score --batch v1-mini
```

The only command that writes scores. Wraps `harness/score.py` and `harness/analyze.py`.

## medomni task new

Creates a task spec from the template.

```bash
medomni task new my-task --dataset vitaldb
```

## medomni task check

Validates a spec, builds its task, confirms nothing leaks to the agent, and checks the fingerprint. With `--batch`, checks every task of a batch against its published fingerprints.

```bash
medomni task check specs/my-task.yaml
```

```bash
medomni task check --batch v1-mini
```

Wraps `data_task/taskbuilder/validate.py`.

## medomni encoder check

Validates an encoder's card, builds its image, runs it on the family's samples, and compares the evidence with the expected responses.

```bash
medomni encoder check encoders/<family>/<encoder>
```

Wraps the encoder gate in `perception/registry.py`.

## Proposed additions

!!! note "Not yet decided"
    The guides need four more commands. They are proposals until the CLI is designed in phase 3.

| Command | Does | Used in |
|---|---|---|
| `medomni data connect <dataset> --path <dir>` | Records where your licensed copy of a dataset is | [Connect your data](../guides/connect-your-data.md) |
| `medomni task build --batch <batch>` | Builds a batch's tasks from your local data | [Connect your data](../guides/connect-your-data.md) |
| `medomni encoders pull <family-or-encoder>` | Pulls encoder images from ghcr.io | [Use the encoders](../guides/use-the-encoders.md) |
| `medomni gateway up` | Starts the gateway on the pulled encoders | [Use the encoders](../guides/use-the-encoders.md) |

## Where next

- [Get started](../get-started.md): the commands in order on a first run.
- [API reference](../api/index.md): the same functions from Python.
- [Contracts](../learn/contracts/index.md): what the check commands enforce.
