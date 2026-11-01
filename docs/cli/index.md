# Commands

Shared commands are at the top level; each project's commands are under its name. Every subcommand prints its options with `--help`, and every check exits 1 on any failure.

## Core

| Command | Does |
|---|---|
| `medomni --version` | Prints the MedOmni version. |
| `medomni plugins` | Lists the installed plug-in packages and what each adds. |
| `medomni contracts check [<contract> ...]` | Validates the contracts: family registry, task spec, task suite, model card, Gateway API, dataset policy, result record, workspace config. |
| `medomni audit` | Runs the [audit](../reference/audit.md) and writes its report to the workspace. |

## Bench

| Command | Does |
|---|---|
| `medomni bench data connect <dataset> --path <dir>` | Records where your copy of a dataset is, in the workspace configuration. |
| `medomni bench data check <dataset>` | Runs the dataset's adapter on its data sample and validates its policy. |
| `medomni bench task new <task-id> --dataset <dataset>` | Creates a task spec from the template. |
| `medomni bench task build --suite <suite>` or `<spec>` | Builds tasks and their atom tasks in the workspace, for every condition. Dummy data for `smoke-dummy` is generated on the fly. |
| `medomni bench task check <spec>` | Checks a spec and the task it builds: fields, metrics, leakage, families, fingerprint. |
| `medomni bench task check --suite <suite>` | Checks every built task of a suite against its published fingerprint. |
| `medomni bench run --agent <config> --suite <suite>` | Checks the route against each dataset policy, pulls the encoder images for the families the tasks stage, runs every atom task in Harbor and records each run. `--condition` (repeatable; default `enc`), `--reps <n>`, `--concurrency <n>`. Resumes where it stopped. |
| `medomni bench score --suite <suite>` | Scores every target of every complete task per agent, condition and repetition, and prints and saves the table. The only command that writes scores. `--agent` limits it to one agent. |

## Perception

| Command | Does |
|---|---|
| `medomni perception pull [<family-or-encoder> ...]` | Pulls encoder images from `ghcr.io/medomni`. |
| `medomni perception up --data-root <dir>` | Starts the gateway on the pulled encoders, on `127.0.0.1:8000`. |
| `medomni perception check <encoder-folder>` | Validates the model card, builds the image, compares its responses on test data with `expected.json`, then runs it on real family samples. `--samples <dir>` gives the samples; `--freeze` records `expected.json` instead. |

## Where next

- [Get started](../get-started.md): the commands in order on a first run.
- [Python API](../api/index.md): the same functions from Python.
