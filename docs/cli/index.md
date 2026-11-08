# Commands

Shared commands are at the top level; each project's commands are under its name. Every subcommand prints its options with `--help`, and every check exits 1 on any failure.

## Core

| Command | Does |
|---|---|
| `medomni --version` | Prints the MedOmni version. |
| `medomni plugins` | Lists the installed plug-in packages and what each adds, arms included. |
| `medomni contracts check [<contract> ...]` | Validates the contracts: family registry, dataset config, dataset policy, recipe, task template, benchmark card, task set, model card, Gateway API, result record, prediction record, workspace config. |
| `medomni cache build <dataset>` | Loads the dataset and runs file conversions into the [cache](../learn/core/cache.md). |
| `medomni cache status` | Lists cache entries per dataset and step, with size and use. |
| `medomni cache verify` | Recomputes every entry's content hash and names any entry that changed. |
| `medomni cache gc [--dry-run]` | Removes entries no current step uses. |

## Bench

| Command | Does |
|---|---|
| `medomni bench data connect <dataset> --path <dir>` | Records where your copy of a dataset is, in the workspace configuration. |
| `medomni bench data check <dataset>` | Checks your copy against the dataset package (version, listed files, needed tables), loads its data sample and dummy data, validates the policy, and checks that every raw value a label reads is classified ([dataset check](../learn/bench/build.md#correctness-checks)). |
| `medomni bench agent new <name>` | Writes an agent config to fill in. |
| `medomni bench data new <dataset>` | Writes a dataset package to fill in, in `bench/datasets/<dataset>/`. |
| `medomni bench task new <template> --dataset <dataset>` | Writes a task template and an `n20` cohort to fill in. |
| `medomni bench task build --set <set>` or `<template>@<cohort>` | Runs [Build](../learn/bench/build.md): atom tasks in the workspace, for every arm the set lists and every evidence variant. Dummy data for `medomni-bench/smoke-dummy` is generated on the fly. |
| `medomni bench task check <template>@<cohort>` | Checks a template, its cohort and the build: fields, metrics, labels, test patients, families, the [correctness checks](../learn/bench/build.md#correctness-checks), and the two [stand-in agents](../learn/bench/scoring.md#checks-before-any-run). |
| `medomni bench task check --set <set>` | Runs the checks of `task check <template>@<cohort>` on every pair the set pins. |
| `medomni bench task check --release` | For MedOmni's releases: checks every pinned pair in every task set, and fails when a pair's cohort, labels, targets, scoring or dataset release changed since the last release and its [version](../learn/bench/tasks.md#version) N has not risen. It compares config files, never data. Builds and runs never use it. |
| `medomni bench run --agent <config> --set <set>` | Checks the route against each dataset policy, pulls the encoder images for the families the tasks stage, runs every atom task in Harbor and records each run. Prints a running count of finished and failed atom tasks. `--arm` (repeatable; default: every arm the set lists), `--reps <n>`, `--concurrency <n>`. Resumes where it stopped. |
| `medomni bench score --set <set>` | Scores every target of every complete `<template>@<cohort>` per agent, arm and repetition, and prints and saves the table. Rows with different config hashes are flagged configured differently. The only command that writes scores. `--agent` limits it to one agent. |

## Perception

| Command | Does |
|---|---|
| `medomni perception pull [<family-or-encoder> ...]` | Pulls encoder images from `ghcr.io/medomni`. |
| `medomni perception up --data-root <dir>` | Starts the gateway on the pulled encoders, on `127.0.0.1:8000`. |
| `medomni perception new <family>/<encoder>` | Writes an encoder folder to fill in, in `perception/encoders/`, with an empty `testdata/`. |
| `medomni perception check <encoder-folder>` | Validates the model card with `contracts check`, builds the image and runs the encoder's tests: compares its responses on test data with `expected.json`, then runs it on real family samples. `--samples <dir>` gives the samples; `--freeze` records `expected.json` instead. |

## Studio

| Command | Does |
|---|---|
| `medomni studio preview <template>@<cohort>` | Runs the cohort on your copy up to the draw and prints the patients left after each step and per class. Builds nothing. |
| `medomni studio download-list <dataset>` | For a dataset downloaded in parts, lists the files its source population needs. |
| `medomni studio dummy <dataset> [--subjects N] [--seed S] [--out DIR]` | Writes dummy data shaped like the dataset, from its `dataset.yaml` and `codes.csv`, with the [dummy-data generator](../learn/core/families.md#how-the-registry-is-used). |
| `medomni studio audit` | Runs the [audit](../reference/audit.md) and writes its report to the workspace. `--only` limits it to some assets. |
| `medomni studio progress <run>` | Shows a run's progress live, per atom task. Run it beside `medomni bench run`. |
| `medomni studio build-sheet <set>` | Writes a sheet of what a set's build made, per task, to the workspace. |
| `medomni studio bench-health <run>` | Reports each encoder's health from a finished run's call log. |
| `medomni studio relevance <template>` | Writes the relevance table that scoring reads for a template. |
| `medomni studio encoder-status` | Lists which encoders are built and which are planned. |
| `medomni studio encoder-demo <encoder>` | Runs an encoder on one sample and prints its evidence. |
| `medomni studio testdata <encoder>` | Writes an encoder's test inputs and `PROVENANCE.md` into its `testdata/`. |
| `medomni studio family-samples <family>` | Writes samples of a family, for real-sample checks. |
| `medomni studio check <tool>` | Checks a tool against its kind's interface. |

## Where next

- [Get started](../get-started.md): the commands in order on a first run.
- [Python API](../api/index.md): the same functions from Python.
