# Tasks

A task asks a clinical question of each patient in a cohort, with a fixed way to score the answers. It is written as a task template and one or more cohorts. Build turns a template and a cohort into atom tasks.

```text
task template + cohort ──Build──▶ <template>@<cohort> ──▶ one atom task per patient, per condition
                                        └──▶ answers (kept apart) + fingerprint
```

## Task template

A YAML file, `template.yaml`, that states:

- **targets**: one or more, each naming a label from the dataset's library and its metric
- **input**: the tables and families the agent may see
- **variants**: the evidence variants to build, `default` and optionally `full`
- **instruction**: the template for the agent's instruction
- **environment**: CPUs, memory, timeouts, no internet

A template is frozen once [Make](../toolkit.md) is done. A changed template is a new template.

## Cohort

A cohort is a [recipe](recipes.md) in its own file next to the template: who is included, at which prediction time, and how many per class. One template can have several cohorts, such as `n20` and `n50`; the patients of `n20` are the first ones of `n50`.

The pair is written `<template>@<cohort>`, such as `mimic_ckd-staging@n20`, and `<template>:full@<cohort>` for the full evidence variant. Each built pair has its own fingerprint.

## Atom task

The unit an agent runs: one patient, all of the targets, at the patient's prediction time. It holds the instruction, the patient's evidence, the environment and a format check. It never holds the answers. The agent writes one prediction per target.

## Fingerprint

A hash of a built `<template>@<cohort>`: its files, instructions, environment and answers. It never includes build time, paths on your machine or the encoders served; the run record holds those. Anyone with the data can rebuild it and check it against the published fingerprint. [Build](build.md#fingerprint-and-step-counts) explains what happens when it differs.

## Task set

A named list of `<template>@<cohort>` pairs pinned to fingerprints, such as `v1`. Task sets are what MedOmni publishes and what scores are compared on.

- A task set only grows: pairs are added, never changed.
- For each pair it also lists the step counts and the hashes of the cache entries the build uses.
- Credentialed task sets publish fingerprints and hashes only; you build them from your own access. See [Rebuild a task set](../../guides/rebuild-a-task-set.md).
- To build outside a task set, for example while writing a cohort, name the pair: `medomni bench task build mimic_ckd-staging@n20`.

## Where it lives

- `bench/datasets/<dataset>/tasks/<template>/`: `template.yaml` and `cohorts/`
- `bench/sets/`: the task sets
- `src/medomni/bench/build/`: Build
- your workspace: the built atom tasks and the cache

## Where next

- [Build](build.md): the steps from template to atom tasks.
- [Tasks reference](../../reference/tasks.md): every template field, the atom task layout and the fingerprint algorithm.
- [Runs](runs.md): how an agent runs atom tasks.
