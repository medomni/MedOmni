# Tasks

The task template, the built files, the config hash, and the benchmarks and their task sets. [Tasks](../learn/bench/tasks.md) explains how they fit together.

Contract: task template, `src/medomni/core/contracts/schemas/task-template.schema.json`. The cohort fields are in [Recipes](recipes.md#cohort-file).

## Tasks in v0.3.0

One folder per template in `bench/datasets/<dataset>/tasks/`, with its cohorts.

- 30 templates on credentialed data: 15 on AI-READI, 9 on MIMIC-IV, 6 on BDSP
- the VitalDB templates on open data
- an `n20` cohort for every template, and a `ladder` cohort for the 5 templates of the modality ladder
- a `full` evidence variant for most templates: the whole record minus the targets' guards

## Task template

`bench/datasets/<dataset>/tasks/<template>/template.yaml`

| Field | Required | Meaning |
|---|---|---|
| `template_id` | yes | `<dataset>_<name>`; equals the folder name. |
| `dataset` | yes | The dataset the template binds to. |
| `authors` | yes | Who wrote the template: name and GitHub handle for each. |
| `targets` | yes | One or more. Each has a `name`, a `label` from the dataset's library, and its `metric`: `auc`, `qwk` or `mae`. |
| `input` | yes | The tables and families the default evidence variant stages. |
| `evidence` | no | The evidence variants: `[default]` (default), or `[default, full]`. Each variant is a task of its own. |
| `exclude` | no | Codes or fields to remove beyond the targets' guards. |
| `agent` | yes | What an agent needs to run the task: the three fields below. |
| `agent.instruction` | yes | The template that renders the agent's instruction. |
| `agent.environment` | yes | CPUs, memory, internet access, agent and verifier timeouts. |
| `agent.submission_path` | yes | Where the agent writes its answer. |

Check a template, its cohort and the build; the exit code is 1 on any failure:

```bash
medomni bench task check <template>@<cohort>
```

## Built files

Build writes each task's content once, then renders it into atom tasks under each arm.

The content is in `atomtasks/_content/<template>@<cohort>/`, such as `atomtasks/_content/mimic-iv_ckd-staging@n20/`:

| Path | Holds |
|---|---|
| the atom list | The task's atom tasks, one per patient. |
| the answers | Each patient's answer for every target. |
| the targets and scoring spec | What is scored, and with which metric. |
| one folder per atom | `record.json`: the evidence the instruction shows, as structured data. |

An atom task is what an agent runs, rendered under `atomtasks/<arm>/<atom>/`, or `atomtasks/<arm>/<variant>/<atom>/` for an arm with variants, such as `atomtasks/modality-ladder/r1/<atom>/`. Rendering stages the patient's files from the cache. Its files are real copies, never links:

| Path | Holds |
|---|---|
| `task.toml` | Task metadata, arm, resources, the `<template>@<cohort>` and the patient. |
| `instruction.md` | The question, the patient's record and the targets to predict. |
| `environment/` | The closed-network containers, with the perception service when the arm attaches it. |
| `tests/` | A format check on the answer. It never scores. |
| `data/` | The patient's staged files, minus anything that leaks a target. |

The answers stay in the content folder; a render never copies them into an atom task. The atom tasks of one `<template>@<cohort>` are scored together against them.

## Config hash

Each `<template>@<cohort>` under each arm, or arm variant, has a config hash: `cfg1:` and the SHA-256 over its config files and two release names. Each file adds its path, its length and its bytes, in path order.

- The files: the template, the cohort, the labels and recipes the task uses, and the arm's definition with its variant.
- The releases: the dataset release and the MedOmni release.

Build writes it to the build manifest, beside the step counts. Run and score records copy it as `config_hash`. The prefix names the algorithm, so published config hashes stay checkable after an upgrade. It covers no data.

`medomni bench task check --release` checks every pinned pair in every task set of the workspace's benchmarks. It fails when a pair's cohort, labels, targets, scoring or dataset release differs from the last release and its N has not risen. It compares config files only. MedOmni runs it before a release; your builds and runs never do.

Result records imported from v0.2 runs are version 0 and carry a `v0.2:` config hash instead, over the v0.2 template's config files. Only imported records may carry one. They name the sets `medomni-bench/v0.2-n20`, `v0.2-noenc`, `v0.2-ladder`, `v0.2-forced` and `v0.2-mid`, one per v0.2 task tree.

## Benchmarks and task sets

A benchmark is one folder, `bench/benchmarks/<benchmark>/`: its card in `benchmark.yaml`, and its task sets in `sets/<set>.yaml`. A task set is named `<benchmark>/<set>`.

Contract: benchmark card, `src/medomni/core/contracts/schemas/benchmark-card.schema.json`.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The benchmark's name; equals the folder name. |
| `version` | yes | The benchmark's own version. |
| `owner` | yes | Who maintains it. |
| `license` | yes | The license of the benchmark's own files. Each dataset keeps its own license. |
| `accepts` | yes | The intelligence kinds it may be run with: `agent`. |

A task set pins each `<template>@<cohort>` at its version N, and nothing else. Task sets only grow, and an entry never changes: a new N enters only a new task set. The set's content hash, `task_set_hash`, covers the pairs and their N.

Contract: task set, `src/medomni/core/contracts/schemas/task-set.schema.json`.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The task set's name, such as `v1`; equals the file name. |
| `description` | no | One line on what it holds. |
| `arms` | yes | The [arms](../learn/bench/runs.md#arms) every pair is built under. |
| `tasks` | yes | One or more entries `{task: <template>@<cohort>, version: <N>}`, with N an integer. Imported v0.2 sets use 0. |

`medomni-bench`, MedOmni's own benchmark: version 1.0, owner MedOmni team, license CC-BY-4.0, accepts `agent`.

| Task set | Data | Arms | Holds |
|---|---|---|---|
| `medomni-bench/smoke-dummy` | Dummy data | `encoders` | One pair per template, on generated data. |
| `medomni-bench/vitaldb` | VitalDB | `encoders`, `no-perception` | The VitalDB templates. |
| `medomni-bench/v1` | AI-READI, MIMIC-IV, BDSP | `encoders`, `no-perception` | The 30 credentialed templates at `n20`. |
| `medomni-bench/modality-ladder` | AI-READI, MIMIC-IV, BDSP | `modality-ladder` | The 5 ladder templates at their `ladder` cohort. |

## Where next

- [Families](families.md): the inputs a template can name.
- [Recipes](recipes.md): the cohort, label and evidence fields.
- [Contribute](../guides/contribute.md): write a new template and cohort.
- [Datasets](datasets.md): what each dataset needs.
