# Build

Build turns a task template, a cohort and your copy of a dataset into atom tasks with a fixed fingerprint. It runs the same way on every machine, and the same inputs give the same atom tasks, byte for byte.

```text
template + cohort + your copy ──Build──▶ atom tasks + answers + fingerprint + step counts
```

`medomni bench task build` runs it. It is the only step that makes atom tasks.

## Make and Build

| | Make | Build |
|---|---|---|
| Project | [Studio](../studio/overview.md) | Bench |
| Who | People: dataset survey, clinician input, review | No one: it runs alone |
| Ends in | A frozen task template and its cohorts | Atom tasks with a fingerprint |
| Same result every time | No | Yes |

A template only reaches Build once Make is done. Build never asks a question and never changes a template.

## Steps

Loading runs once per dataset and is kept in the [cache](../core/cache.md). The task steps run for each `<template>@<cohort>`.

**Loading** (from the [dataset package](datasets.md#loading)):

1. **Verify:** the copy is the dataset version the package describes, and every file it lists exists.
2. **Read:** the format readers read the tables and files the package names, and only those.
3. **Rules:** the package's timing and visit rules are applied.
4. **Write:** the result is the dataset's event table.
5. **Check:** one row per event, every code in the dataset's code list, every `FILE` path present.

**Family conversion:** each file in a format no family accepts is converted once by a [family converter](../core/families.md#family-converters).

**Task steps** (from the [recipe](recipes.md)):

1. **Source population:** the patients the cohort may draw from, chosen by a hash rule.
2. **Prediction time:** each patient's anchor event and offset.
3. **Requirements:** the events and files each patient must have, in their windows.
4. **Labels:** each target's answer, from the dataset's label library.
5. **File check:** every file the patient would see converts and matches its family. This runs before the draw, so the pool does not depend on the seed.
6. **Draw:** the patients are ranked by hash within each class and the first n are taken.
7. **Evidence:** for each patient, the rows and files before the prediction time, minus the leakage guard.
8. **Render:** one atom task per patient and condition, and the answers in a separate folder.
9. **Check:** the atom tasks are validated, the staged files are scanned for any answer, and the fingerprint and step counts are written.

Build stops, and names the step, when:

- the recipe needs a kind of time the dataset does not have, such as hours on a dataset with visit dates only
- a class has fewer patients than the draw needs
- a staged file contains an answer

## Fingerprint and step counts

- The **fingerprint** is a hash of the built content: files, instructions, environment and answers. It never includes build time, local paths or the encoders served. The algorithm is in [Tasks reference](../../reference/tasks.md#fingerprint).
- The **step counts** are the number of patients left after each task step, from the source population to the draw. They are stored with the fingerprint. Both are counts and hashes only, so they can be published for every dataset.

When your fingerprint differs from the published one, Build warns and does not stop. The step counts show the first step that differs. Runs on a build that differs are recorded apart and never compared with published scores.

## Evidence variants

A template lists its evidence variants. Each variant is built and fingerprinted on its own.

- **default:** the tables and families the template names
- **full:** every table and family the dataset has, minus the leakage guard

The full variant is written `<template>:full@<cohort>`.

## Where it lives

- `src/medomni/bench/build/`: the steps, the draw, the checks and the fingerprint
- `src/medomni/core/recipes/`: the recipe format Build reads
- your workspace: the cache and the built atom tasks

## Where next

- [Recipes](recipes.md): the format that says who, when, which answer and which evidence.
- [Cache](../core/cache.md): what Build keeps between runs.
- [Tasks](tasks.md): templates, cohorts and task sets.
