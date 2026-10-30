# Tasks

A task type is defined by a spec. The task builder turns a spec and your data into atom tasks, one per patient, and a fingerprint proves the result matches anyone else's build.

## Task types in v0.2.1

30 task types, one spec each in `data_task/taskbuilder/specs/`: 15 on AI-READI, 9 on MIMIC-IV and 6 on BDSP. Each type also has a `-mini` spec (a small cohort), and 28 have a `-full` spec (the whole record minus inputs that leak the answer).

## Task spec

| Field | Required | Meaning |
|---|---|---|
| `task_id` | yes | `<dataset>_<name>`, with `-full` or `-mini` for those versions. |
| `dataset` | yes | The dataset the task binds to. |
| `seed` | yes | Seed for cohort sampling. |
| `target` | yes | What is predicted, how the label is derived, and its `metric` (`accuracy`, `auc`, `brier`, `qwk`, `macro_auc`, `mae`). |
| `cohort` | yes | Who is in the cohort, and how many per class. |
| `input` | yes | The evidence the agent may see, by stream and family. |
| `environment` | yes | CPUs, memory, internet access, agent and verifier timeouts. |
| `submission_path` | yes | Where the agent writes its answer. |
| `instruction` | yes | The template that renders the agent's instruction. |
| `evidence_mode` | no | `selected` (default), `full` or `mini`. |
| `prediction_time` | no | The time after which nothing is evidence. |
| `excluded_from_inputs` | no | Inputs banned because they leak the target. |
| `extends` | no | A base spec merged underneath this one. |

Check a spec and the task it emits; the report is JSON and the exit code is 1 on any failure:

```bash
python data_task/taskbuilder/validate.py data_task/taskbuilder/specs/<task-id>.yaml
```

## Atom task

What an agent runs, in `data_task/atomtasks/<atom>/` (`atomtasks-noenc/` and `atomtasks-forced/` for the other conditions):

| Path | Holds |
|---|---|
| `task.toml` | Task metadata, condition, resources, and the parent task type and patient. |
| `instruction.md` | The question, the patient's record and the targets to predict. |
| `environment/` | The closed-network containers, with the perception sidecar when encoders are available. |
| `tests/` | A format check on the answer. It never scores. |
| `data/` | The patient's staged files, minus anything that leaks a target. |

The answers sit with the task type, in `atomtasks/_parents/<task type>/`, never in an atom task. The atom tasks of one type are scored together against them.

**Leakage is blocked at build time.** Inputs that would reveal a target are banned from the evidence, based on how the target is derived (the leakage rules in `data_task/taskbuilder/registry/`), and the builder scans the staged files and fails the build on a hit.

## Fingerprint

A task's fingerprint is the SHA-256 over every file in its folder, in path order, each file's relative path followed by its bytes, excluding `FINGERPRINT` itself. It is written to the folder's `FINGERPRINT` file. `validate.py` recomputes it and fails if it differs.

A fingerprint is never changed in place: a changed task is a new task, rebuilt and re-pinned. A score is refused if the runs of one task type carry different fingerprints.

## Batches

A batch pins task ids to fingerprints, in `data_task/tasks/batches/<name>.yaml`. `pin_batch.py <batch> <task-id> ...` rewrites the whole file from the ids it is given.

| Batch | Tasks |
|---|---|
| `v1-mini` | The 30 `-mini` tasks. |
| `v1-full` | All 88 specs: 30 types, 30 `-mini`, 28 `-full`. |
| `first-batch` | 3 earlier tasks on MIMIC-IV and BDSP. |
| `stage1` | 2 earlier tasks on MIMIC-IV. |

Credentialed tasks publish fingerprints, never task data: build them from your own access and compare. See [Connect your data](../guides/connect-your-data.md).

## Where next

- [Families](families.md): the inputs a spec can name.
- [Contribute](../guides/contribute.md): write a new spec.
- [Datasets](datasets.md): what each dataset needs.
