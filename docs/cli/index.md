# Commands

Shared commands are at the top level; each project's commands are under its name. Every subcommand prints its options with `--help`, and every check exits 1 on any failure.

## Core

| Command | Does |
|---|---|
| `medomni --version` | Prints the MedOmni version. |
| `medomni plugins` | Lists the installed plug-in packages and what each adds. |
| `medomni contracts check [<contract> ...]` | Validates the contracts: family registry, dataset config, dataset policy, recipe, task template, task set, model card, Gateway API, result record, workspace config. |
| `medomni cache build <dataset>` | Loads the dataset and runs file conversions into the [cache](../learn/core/cache.md). |
| `medomni cache status` | Lists cache entries per dataset and step, with size and use. |
| `medomni cache verify [--set <set>]` | Recomputes every entry's content hash; with `--set`, compares with the task set's published hashes. |
| `medomni cache gc [--dry-run]` | Removes entries no current step uses. |

## Bench

| Command | Does |
|---|---|
| `medomni bench data connect <dataset> --path <dir>` | Records where your copy of a dataset is, in the workspace configuration. |
| `medomni bench data check <dataset>` | Checks your copy against the dataset package (version, listed files, needed tables), loads its data sample and dummy data, and validates the policy. |
| `medomni bench agent new <name>` | Writes an agent config to fill in. |
| `medomni bench data new <dataset>` | Writes a dataset package to fill in, in `bench/datasets/<dataset>/`. |
| `medomni bench task new <template> --dataset <dataset>` | Writes a task template and an `n20` cohort to fill in. |
| `medomni bench task build --set <set>` or `<template>@<cohort>` | Runs [Build](../learn/bench/build.md): atom tasks in the workspace, for every condition and evidence variant. Dummy data for `smoke-dummy` is generated on the fly. |
| `medomni bench task check <template>@<cohort>` | Checks a template, its cohort and the build: fields, metrics, labels, test patients, leakage, families, fingerprint, and the two [stand-in agents](../learn/bench/scoring.md#checks-before-any-run). |
| `medomni bench task check --set <set>` | Checks every build in a task set against its published fingerprint, and prints the step counts of any that differ. |
| `medomni bench run --agent <config> --set <set>` | Checks the route against each dataset policy, pulls the encoder images for the families the tasks stage, runs every atom task in Harbor and records each run. `--condition` (repeatable; default `enc`), `--reps <n>`, `--concurrency <n>`. Resumes where it stopped. |
| `medomni bench score --set <set>` | Scores every target of every complete `<template>@<cohort>` per agent, condition and repetition, and prints and saves the table. Runs on builds that differ from the published fingerprint are scored in a separate table. The only command that writes scores. `--agent` limits it to one agent. |

## Perception

| Command | Does |
|---|---|
| `medomni perception pull [<family-or-encoder> ...]` | Pulls encoder images from `ghcr.io/medomni`. |
| `medomni perception up --data-root <dir>` | Starts the gateway on the pulled encoders, on `127.0.0.1:8000`. |
| `medomni perception new <family>/<encoder>` | Writes an encoder folder to fill in, in `perception/encoders/`. |
| `medomni perception check <encoder-folder>` | Validates the model card, builds the image, compares its responses on test data with `expected.json`, then runs it on real family samples. `--samples <dir>` gives the samples; `--freeze` records `expected.json` instead. |

## Studio

| Command | Does |
|---|---|
| `medomni studio preview <template>@<cohort>` | Runs the cohort on your copy up to the draw and prints the patients left after each step and per class. Builds nothing. |
| `medomni studio download-list <dataset>` | For a dataset downloaded in parts, lists the files its source population needs. |
| `medomni studio dummy <dataset> [--subjects N] [--seed S] [--out DIR]` | Writes dummy data shaped like the dataset, from its `dataset.yaml` and `codes.csv`, with the [dummy-data generator](../learn/core/families.md#how-the-registry-is-used). |
| `medomni studio audit` | Runs the [audit](../reference/audit.md) and writes its report to the workspace. `--only` limits it to some assets. |
| `medomni studio check <tool>` | Checks a tool against its kind's interface. |

## Where next

- [Get started](../get-started.md): the commands in order on a first run.
- [Python API](../api/index.md): the same functions from Python.
