# Tasks

The task template, the atom task layout, the fingerprint algorithm and the task sets. [Tasks](../learn/bench/tasks.md) explains how they fit together.

Contract: task template, `src/medomni/core/contracts/schemas/task-template.schema.json`. The cohort fields are in [Recipes](recipes.md#cohort-file).

## Tasks in v0.3.0

One folder per template in `bench/datasets/<dataset>/tasks/`, with its cohorts.

- 30 templates on credentialed data: 15 on AI-READI, 9 on MIMIC-IV, 6 on BDSP
- the VitalDB templates on open data
- an `n20` cohort for every template, and a `ladder` cohort for the modality ladder
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
| `variants` | no | `[default]` (default), or `[default, full]`. |
| `exclude` | no | Codes or fields to remove beyond the targets' guards. |
| `agent` | yes | What an agent needs to run the task: the three fields below. |
| `agent.instruction` | yes | The template that renders the agent's instruction. |
| `agent.environment` | yes | CPUs, memory, internet access, agent and verifier timeouts. |
| `agent.submission_path` | yes | Where the agent writes its answer. |

Check a template, its cohort and the build; the exit code is 1 on any failure:

```bash
medomni bench task check <template>@<cohort>
```

## Atom task

What an agent runs, built in the workspace under `atomtasks/<condition>/<atom>/`:

| Path | Holds |
|---|---|
| `task.toml` | Task metadata, condition, resources, the `<template>@<cohort>` and the patient. |
| `instruction.md` | The question, the patient's record and the targets to predict. |
| `environment/` | The closed-network containers, with the perception service when encoders are available. |
| `tests/` | A format check on the answer. It never scores. |
| `data/` | The patient's staged files, minus anything that leaks a target. |

The answers sit apart, in `atomtasks/_parents/<template>@<cohort>/`, never in an atom task. The atom tasks of one `<template>@<cohort>` are scored together against them.

## Fingerprint

The fingerprint of a built `<template>@<cohort>` is the SHA-256 over every file in its folder, in path order. Each file adds its relative path, a separator, its length and its bytes. `FINGERPRINT` itself is excluded, and no file holds a build time or a local path. It is written to the folder's `FINGERPRINT` file as `fp1:<hex>`, where `fp1` names this algorithm. A later algorithm gets a new prefix, so published fingerprints stay checkable across releases. `medomni bench task check` recomputes it and fails if it differs.

## Task sets

A task set pins `<template>@<cohort>` pairs to fingerprints, in `bench/sets/<name>.yaml`. For each pair it also lists the step counts and the cache keys and content hashes the build uses. Task sets only grow.

Contract: task set, `src/medomni/core/contracts/schemas/task-set.schema.json`.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The task set's name, such as `v1`. |
| `description` | no | One line on what it holds. |
| `card` | no | The task set's card, below. |
| `tasks` | yes | One or more entries, each a `<template>@<cohort>` with its fingerprint, step counts and cache hashes. |

The card:

| Field | Required | Meaning |
|---|---|---|
| `version` | yes | The task set's own version. |
| `owner` | yes | Who maintains it. |
| `license` | yes | The license of the task set file. |
| `accepts` | yes | The intelligence kinds it may be run with: `agent`. |

| Task set | Data | Holds |
|---|---|---|
| `smoke-dummy` | Dummy data | One pair per template, on generated data. |
| `vitaldb` | VitalDB | The VitalDB templates. |
| `v1` | AI-READI, MIMIC-IV, BDSP | The 30 credentialed templates at `n20`. |

## Where next

- [Families](families.md): the inputs a template can name.
- [Recipes](recipes.md): the cohort, label and evidence fields.
- [Contribute](../guides/contribute.md): write a new template and cohort.
- [Datasets](datasets.md): what each dataset needs.
