# Tasks

A task asks a clinical question of each patient in a cohort, with a fixed way to score the answers. It is written as a task template and one or more cohorts. Build turns a template and a cohort into atom tasks.

```text
task template + cohort ──Build──▶ content of <template>@<cohort>, with the answers
                                        └──▶ one atom task per patient, per arm + config hash
```

## Task template

A YAML file, `template.yaml`, that states:

- **targets**: one or more, each naming a label from the dataset's library and its metric, and optionally its own question
- **input**: the tables and families the proposal named, kept as a record; the evidence is the patient's whole record minus the targets' guards
- **evidence**: the evidence variants; v0.3.0 builds `default` only
- **agent**: what an agent needs to run the task:
    - **statement**: the clinical question, which opens every atom task's instruction
    - **instruction**: the template's own paragraph on the prediction time
    - **environment**: CPUs, memory, timeouts, no internet
    - **submission path**: where the agent writes its answer

A template is frozen once its proposal is signed off in [Studio](../studio/overview.md). A later change to it raises the [version](#version) of each of its cohorts.

## Cohort

A cohort is a [recipe](recipes.md) in its own file next to the template: who is included, at which prediction time, and how many per class. One template can have several cohorts, such as `n20` and `n50`; the patients of `n20` are the first ones of `n50`.

The pair is written `<template>@<cohort>`, such as `mimic-iv_ckd-staging@n20`. Each pair is one task.

## Version

Each task has a version `N.X`, kept as `version:` in its cohort file. Tasks start at 1.0.

- **N** rises when results stop being comparable: a change to the dataset release, the cohort, the labels, the targets or the scoring.
- **X** rises for any other change, such as the instruction's wording or how atom tasks are rendered.
- A change to the template raises the version of each of its cohorts.
- Task sets pin N. A change to X reaches every task set that holds the task; a new N enters only a new task set.

## Atom task

The unit an agent runs: one patient, all of the targets, at the patient's prediction time. It holds the instruction, the patient's evidence, the environment and a format check. It never holds the answers. The agent writes one prediction per target.

## Config hash

A hash of the config a task is built from under one arm: the template, the cohort, the labels and recipes it uses, the arm's definition, and the dataset and MedOmni releases. Runs with the same config hash used the same task configuration. Scores with different config hashes in one table are flagged; see [Scoring](scoring.md#refusals-and-failures).

The config hash covers no data; see [Design principles](../principles.md#task-reproducibility).

## Task set

A named list of `<template>@<cohort>` pairs, each pinned at its version N, such as `v1`, and the [arms](runs.md#arms) to build them under. Task sets are what MedOmni publishes and what scores are compared on.

- A task set only grows: pairs are added, never changed. A new N of a pair enters only a new task set, such as `v2`.
- Its content hash covers every pair and its N. Each score record carries the hash, and scores with different hashes are never put in one table.
- Credentialed task sets publish configs only; you build them from your own access. See [Rebuild a task set](../../guides/rebuild-a-task-set.md).
- Build builds every pair under every arm the set lists.
- To build outside a task set, for example while writing a cohort, name the pair: `medomni bench task build mimic-iv_ckd-staging@n20`.

## Benchmark

A benchmark holds several task sets under one card: its name, version, owner, license and the intelligence kinds it accepts. It is one folder, `bench/benchmarks/<benchmark>/`, with the card in `benchmark.yaml` and its task sets in `sets/`.

- A task set is named `<benchmark>/<set>`, such as `medomni-bench/v1`, so two benchmarks can each have a `v1`.
- MedOmni's own benchmark is `medomni-bench`. A plug-in package publishes its own benchmark as the same folder; see [Plug-ins](../core/plugins.md).

## Where it lives

- `bench/datasets/<dataset>/tasks/<template>/`: `template.yaml` and `cohorts/`
- `bench/benchmarks/<benchmark>/`: a benchmark's card and its task sets
- `src/medomni/bench/build/`: Build
- your workspace: the built atom tasks and the cache

## Where next

- [Build](build.md): the steps from template to atom tasks.
- [Tasks reference](../../reference/tasks.md): every template field, the built files, the config hash and the benchmark files.
- [Runs](runs.md): how an agent runs atom tasks.
