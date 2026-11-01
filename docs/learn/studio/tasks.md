# Tasks

A task is a clinical question asked of each patient in a cohort, with a fixed way to score the answers. A task spec defines it; the task pipeline turns the spec and your data into atom tasks.

```text
task spec + dataset ──task pipeline──▶ task ──▶ one atom task per patient, per condition
                                         └──▶ answers (kept apart) + fingerprint
```

## Task spec

A YAML file that states:

- **targets**: one or more, each with what is predicted, how its label is derived, and its metric
- **cohort**: who is included, and how many per class
- **prediction time**: the moment after which nothing is evidence
- **input**: the families the agent may see
- **instruction**: the template for the agent's instruction
- **environment**: CPUs, memory, timeouts, no internet

## Task pipeline

`medomni bench task build` runs the spec through one shared pipeline. Only the first step is dataset code.

1. **Adapter:** the dataset's adapter reads your copy.
2. **Index:** what each patient has, by family and time.
3. **Derivations:** each target's label, from the spec's rule.
4. **Cohort:** the patients who meet the spec, sampled with its seed.
5. **Leakage guard:** inputs that would reveal a target are removed, and the staged files are scanned; a target found in them fails the build.
6. **Render:** one atom task per patient for each condition, and the answers in a separate folder.
7. **Check:** the task is validated and its fingerprint computed.

!!! warning "Designed later in Stage 1"
    The steps above are the outline. Each step's inputs and outputs are designed from probes of the v0.2 specs and of the four datasets.

The same spec on the same data builds the same task, byte for byte.

## Atom task

The unit an agent runs: one patient, all of the task's targets, at the task's prediction time. It holds the instruction, the patient's files, the environment and a format check. It never holds the answers. The agent writes one prediction per target.

## Fingerprint

A hash of the task's content: its files, instruction, environment and answers. It never includes build time or paths on your machine. Anyone with the data can rebuild the task and check it against the published fingerprint. A changed task is a new task with a new fingerprint. Scores are refused for runs whose fingerprints differ.

## Batch

A named list of task ids pinned to fingerprints, such as `v1-mini`. Batches only grow: tasks are added, never changed. Credentialed batches publish fingerprints only; you build them from your own access.

## Where it lives

- `bench/specs/`: one spec per task
- `bench/batches/`: the batches
- `src/medomni/bench/tasks/`: the task pipeline
- your workspace: built tasks, their atom tasks, and the pipeline's caches

## Where next

- [Tasks reference](../../reference/tasks.md): every spec field, the atom task layout and the fingerprint algorithm.
- [Runs](runs.md): how an agent runs atom tasks.
