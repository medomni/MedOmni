# Build

Build turns a task template, a cohort and your copy of a dataset into atom tasks. It runs the same way on every machine, and the same inputs give the same atom tasks, byte for byte.

```text
template + cohort + your copy ──Build──▶ content + step counts ──▶ atom tasks per arm + config hash
```

`medomni bench task build` runs it. It is the only step that makes atom tasks.

## Make and Build

| | Make | Build |
|---|---|---|
| Project | [Studio](../studio/overview.md) | Bench |
| Who | People: dataset survey, clinician input, review | No one: it runs alone |
| Ends in | A frozen task template and its cohorts | Atom tasks and their config hashes |
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

1. **Source population:** the patients the cohort may select from, chosen by a hash rule.
2. **Prediction time:** each patient's anchor event and offset.
3. **Requirements:** the events and files each patient must have, in their windows.
4. **Labels:** each target's answer, from the dataset's label library.
5. **Cohort selection and file check:** the patients are ranked by hash within each class and taken from the top until each class has its share. When the cohort requires files to convert (`converts`), each patient's files are converted and checked against their families on the way down, and a patient whose files fail is replaced by the next one in rank. The patients selected are the ones a check of the whole pool would give; only their files are converted.
6. **Evidence:** for each patient, the whole record up to the prediction time, minus the guards of every target. A file with no time of its own that holds later rows is cut at the prediction time when its family is listed in the evidence rules' `files.crop`.
7. **Content:** written once per task: the atom list, the answers, the targets and scoring, and for each patient `record.json`, the evidence the instruction shows. The content checks run on it.
8. **Render:** one atom task per patient under each arm the task set lists, with the patient's files staged from the cache and what the arm adds or masks. The answers are never copied in.
9. **Check:** the atom tasks are validated and pass the atom task checks, and the config hashes and step counts are written to the build manifest.

Build stops, and names the step, when the recipe needs a kind of time the dataset does not have, such as hours on a dataset with visit dates only, or when a correctness check fails.

## Correctness checks

Build runs `medomni bench task check` on what it builds and writes no task that fails a check. It stops and names the check and the target or patient. The checks are in Bench, so a task is checked whether or not anyone runs Studio.

**Content checks**, after the content step:

- **No answer in the evidence:** no row or file of a patient's evidence holds a target's answer or a field its label guards.
- **Eligible at the prediction time:** each patient meets the cohort's requirements at the prediction time, such as an admission that is still open.
- **Events still ahead:** for an event target, no positive patient's event is at or before the prediction time.
- **Enough patients:** each target cohort selection balances on (`select.by`) has at least 5 selected patients in each class, or at least 2 distinct values if it is numeric. Any other target that falls short is marked in the content and left out of scoring.
- **Answers that vary:** a target's answers over the source population are not all the same. If they are, the whole task is refused, and its cohort or target must change.

**Atom task checks**, after rendering:

- **No image after the prediction time:** every staged image is dated at or before the prediction time.
- **Complete recordings:** every staged WFDB header comes with its signal files and segments.
- **Closed network:** every container of an atom task is on one internal network, with no route out.

**Dataset check**, in `medomni bench data check`:

- **Every label value classified:** each raw value a label reads is classified in the dataset's label library.

## Config hash and step counts

- The **config hash** of each task under each arm covers its config files and the releases, never data. The algorithm is in [Tasks reference](../../reference/tasks.md#config-hash).
- The **step counts** are the number of patients left after each task step, from the source population to cohort selection. With a file check, `file check tried` counts the patients whose files were checked, and `file check` counts the eligible patients less those that failed; the pool before cohort selection is the eligible patients, not yet confirmed to convert. They show where two builds of one task part ways: the build manifest stays local, and two people can compare their counts by hand.

Both are written to the build manifest, and both are hashes and counts only.

## Evidence

The evidence of each patient is the whole record up to the prediction time, minus the guards of every target. The template's `input` and `exclude` do not narrow it: they record what the task's proposal asked for.

v0.3.0 builds one evidence variant, `default`. Build refuses a pair written `<template>:full@<cohort>`.

## Where it lives

- `src/medomni/bench/build/`: the steps, cohort selection, the checks and the config hash
- `src/medomni/core/recipes/`: the recipe format Build reads
- your workspace: the cache and the built atom tasks

## Where next

- [Recipes](recipes.md): the format that says who, when, which answer and which evidence.
- [Cache](../core/cache.md): what Build keeps between runs.
- [Tasks](tasks.md): templates, cohorts and task sets.
