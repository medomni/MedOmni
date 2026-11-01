# Tasks

A task is a clinical question asked of each patient in a cohort, with one fixed way to score the answers. A task spec defines it; the task builder turns the spec and your data into atom tasks.

```text
task spec + dataset ──build──▶ task ──▶ one atom task per patient, per condition
                                  └──▶ answers (kept apart) + fingerprint
```

## Task spec

A YAML file that states:

- **target**: what is predicted, how the label is derived, and the metric
- **cohort**: who is included, and how many per class
- **prediction time**: the moment after which nothing is evidence
- **input**: the families the agent may see
- **instruction**: the template for the agent's instruction
- **environment**: CPUs, memory, timeouts, no internet

## Build

`medomni bench task build` turns a spec into a task:

1. The adapter finds the cohort and extracts each patient's files up to the prediction time.
2. Inputs that would reveal a target are removed.
3. The builder scans the staged files and fails the build if a target appears.
4. It writes one atom task per patient for each condition, and the answers to a separate folder.
5. It computes the task's fingerprint.

The same spec on the same data builds the same task, byte for byte.

## Atom task

The unit an agent runs: one patient, all of the task's targets, at the task's prediction time. It holds the instruction, the patient's files, the environment and a format check. It never holds the answers. The agent writes one prediction per target.

## Fingerprint

A hash of the task's files. Anyone with the data can rebuild the task and check it against the published fingerprint. A changed task is a new task with a new fingerprint. Scores are refused for runs whose fingerprints differ.

## Batch

A named list of task ids pinned to fingerprints, such as `v1-mini`. Batches only grow: tasks are added, never changed. Credentialed batches publish fingerprints only; you build them from your own access.

## Where it lives

- `bench/tasks/specs/`: one spec per task
- `bench/tasks/batches/`: the batches
- `bench/tasks/builder/`: the task builder
- your workspace: built tasks and their atom tasks

## Where next

- [Tasks reference](../../reference/tasks.md): every spec field, the atom task layout and the fingerprint algorithm.
- [Runs](runs.md): how an agent runs atom tasks.
