# Commands

Shared commands are at the top level; each project's commands are under its name. Every subcommand prints its options with `--help`, and every check exits 1 on any failure.

## Core

| Command | Does |
|---|---|
| `medomni --version` | Prints the MedOmni version. |
| `medomni plugins` | Lists the installed plug-in packages and what each adds, arms included. |
| `medomni contracts check [<contract> ...]` | Validates every contract file in the repository and in the installed plug-in packages: family registry, dataset config, dataset policy, recipe, task template, agent config, benchmark card, task set, model card. Name `families`, `datasets`, `policies`, `recipes`, `templates`, `agents`, `benchmarks`, `sets` or `cards` to check only those. |
| `medomni cache build <dataset>` | Loads the dataset's event table into the [cache](../learn/core/cache.md). |
| `medomni cache status` | Lists the cached results per dataset and step, with size and use. `folder` backend only. |
| `medomni cache gc [--dry-run]` | Removes results no current step uses, and unfinished folders. `folder` backend only. |

## Bench

| Command | Does |
|---|---|
| `medomni bench data connect <dataset> --path <dir>` | Records where your copy of a dataset is, in the workspace configuration. |
| `medomni bench agent new <name>` | Writes an agent config to fill in. |
| `medomni bench run --agent <config> --set <set>` | Runs the [checks on built tasks](../learn/core/built-tasks.md#checks-on-any-built-task), the [stand-in agents](../learn/bench/scoring.md#stand-in-agents) and the route check on the built set, and runs nothing if one fails. Then pulls the encoder images for the families the tasks stage, runs every atom task in Harbor and records each run. Prints a running count of finished and failed atom tasks. `--arm` (repeatable; default: every arm the set lists), `--reps <n>`, `--concurrency <n>`. Resumes where it stopped. |
| `medomni bench score --set <set>` | Scores every target of every complete `<template>@<cohort>` per agent, arm and repetition, and prints and saves the table. Rows with different config hashes are flagged configured differently. The only command that writes scores. `--agent` limits it to one agent. |

## Perception

| Command | Does |
|---|---|
| `medomni perception pull [<family-or-encoder> ...]` | Pulls encoder images from `ghcr.io/medomni`. |
| `medomni perception up --data-root <dir>` | Starts the gateway on the pulled encoders, on `127.0.0.1:8000`. |
| `medomni perception new <family>/<encoder>` | Writes an encoder folder to fill in, in `perception/encoders/`, with an empty `testdata/`. |
| `medomni perception check <encoder-folder>` | Validates the model card with `contracts check`, checks the Dockerfile's torch installs, builds the image, checks the torch inside it is a listed CPU build, and runs the encoder's tests: compares its responses on test data with `expected.json`, then on real family samples from `--samples <dir>`, or reports that stage unverified without them; `--freeze` records `expected.json` instead; `--record` writes a passing encoder into `perception/deployed.yaml`, the images the perception service starts. |

## Studio

| Command | Does |
|---|---|
| `medomni studio data new <dataset>` | Writes a dataset package to fill in, in `studio/datasets/<dataset>/`. |
| `medomni studio data check <dataset>` | Checks the package's files and policy, writes and loads its dummy data, and checks your copy: version, listed files, the columns the readers need, each hook's problems, and that every raw value a label reads is classified ([dataset check](../learn/studio/build.md#correctness-checks)). It never loads your copy; `medomni cache build` does. |
| `medomni studio task new <template> --dataset <dataset>` | Writes a task template and an `n20` cohort to fill in. |
| `medomni studio task build --set <set>` or `<template>@<cohort>` | Runs [Build](../learn/studio/build.md), the `medomni-v1` builder: built tasks in the workspace, for every arm the set lists. `--set` rebuilds a published set from your copy, with the builder the set names. A pair alone is built under `encoders`, or under the arms `--arm` names. Dummy data for `medomni-bench/smoke-dummy` is generated on the fly. |
| `medomni studio task check <template>@<cohort>` | Checks a template, its cohort and the build: fields, metrics, labels, test patients, families, the builder's [correctness checks](../learn/studio/build.md#correctness-checks), and Core's [checks on built tasks](../learn/core/built-tasks.md#checks-on-any-built-task). |
| `medomni studio task check --set <set>` | Runs the checks of `task check <template>@<cohort>` on every pair the set pins. |
| `medomni studio task check --release` | For MedOmni's releases: checks every pinned pair in every task set, and fails when a pair's cohort, labels, targets, scoring or dataset release changed since the last release and its [version](../learn/studio/tasks.md#version) N has not risen. It compares config files, never data. Builds and runs never use it. |
| `medomni studio survey <dataset>` | Reports what a dataset has: codes, families, time spans and counts, from its event table. |
| `medomni studio census <set>` | For each built pair and arm of a set: the families staged and the spread of the answers. |
| `medomni studio intake <file>` | Turns the rows of an intake form into draft proposals, or a signed-off proposal into a task template. |
| `medomni studio review-form <template>@<cohort>` | Writes the task's clinical review form. `--submit <file>` records a filled-in form as the task's review. |
| `medomni studio preview <template>@<cohort>` | Runs the cohort on your copy up to cohort selection and prints the patients left after each step and per class. Builds nothing. |
| `medomni studio download-list <dataset>` | Lists what to download for a dataset: one tab-separated line per entry, with its source, its path in your copy and how to fetch it (`file`, `folder` or `gunzip`). Without the index tables on disk, it prints those first. |
| `medomni studio dummy <dataset> [--subjects N] [--seed S] [--out DIR]` | Writes dummy data shaped like the dataset, from its `dataset.yaml` and `codes.csv`, with the [dummy-data generator](../learn/core/families.md#how-the-registry-is-used). |
| `medomni studio audit` | Runs the [audit](../reference/audit.md) and writes its report to the workspace. `--only` limits it to some assets. |
| `medomni studio progress <run>` | Shows a run's progress live, per atom task. Run it beside `medomni bench run`. |
| `medomni studio build-sheet <set>` | Writes a sheet of what a set's build made, per task, to the workspace. |
| `medomni studio bench-health <run>` | Reports each encoder's health from a finished run's call log. |
| `medomni studio tables` | Writes the results table of the scored runs. `--set <set>` limits it to one task set. |
| `medomni studio diagrams <description>` | Draws the architecture diagrams from one YAML description, as SVG files that also open in draw.io. |
| `medomni studio relevance <template>` | Writes the relevance table that scoring reads for a template. |
| `medomni studio encoder-status` | Lists which encoders are built and which are planned. |
| `medomni studio encoder-demo <encoder>` | Runs an encoder on one sample and prints its evidence. |
| `medomni studio testdata <encoder>` | Writes an encoder's test inputs and `PROVENANCE.md` into its `testdata/`. |
| `medomni studio family-samples <family>` | Writes samples of a family from your copy of a dataset, for real-sample checks. They hold patient data and stay in your workspace. |
| `medomni studio check <tool>` | Checks a tool against its kind's interface. |

## Where next

- [Get started](../get-started.md): the commands in order on a first run.
- [Python API](../api/index.md): the same functions from Python.
