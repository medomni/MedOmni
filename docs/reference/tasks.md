# Tasks

The task spec, the atom task layout, the fingerprint algorithm and the batches. [Tasks](../learn/bench/tasks.md) explains how they fit together.

Contract: task spec v1, `core/contracts/schemas/task-spec.schema.json`

## Tasks in v0.3.0

One spec per task in `bench/tasks/specs/`.

- 30 tasks on credentialed data: 15 on AI-READI, 9 on MIMIC-IV, 6 on BDSP
- the VitalDB tasks on open data
- a `-mini` spec for every task: a small cohort
- a `-full` spec for most tasks: the whole record minus inputs that leak the answer

## Task spec

| Field | Required | Meaning |
|---|---|---|
| `task_id` | yes | `<dataset>_<name>`, with `-full` or `-mini` for those versions. |
| `dataset` | yes | The dataset the task binds to. |
| `authors` | yes | Who wrote the task: name and GitHub handle for each. |
| `seed` | yes | Seed for cohort sampling. |
| `target` | yes | What is predicted, how the label is derived, and its `metric` (`accuracy`, `auc`, `brier`, `qwk`, `macro_auc`, `mae`). |
| `cohort` | yes | Who is in the cohort, and how many per class. |
| `input` | yes | The evidence the agent may see, by stream and family. |
| `environment` | yes | CPUs, memory, internet access, agent and verifier timeouts. |
| `submission_path` | yes | Where the agent writes its answer. |
| `instruction` | yes | The template that renders the agent's instruction. |
| `evidence_mode` | no | `selected` (default), `full` or `mini`. |
| `prediction_time` | no | The time after which nothing is evidence. |
| `excluded_from_inputs` | no | Extra inputs to ban, beyond those banned automatically from how the target is derived. |
| `extends` | no | A base spec merged underneath this one. |

Check a spec and the task it builds; the exit code is 1 on any failure:

```bash
medomni bench task check bench/tasks/specs/<task-id>.yaml
```

## Atom task

What an agent runs, built in the workspace under `atomtasks/<condition>/<atom>/`:

| Path | Holds |
|---|---|
| `task.toml` | Task metadata, condition, resources, and the parent task and patient. |
| `instruction.md` | The question, the patient's record and the targets to predict. |
| `environment/` | The closed-network containers, with the perception sidecar when encoders are available. |
| `tests/` | A format check on the answer. It never scores. |
| `data/` | The patient's staged files, minus anything that leaks a target. |

The answers sit with the task, in `atomtasks/_parents/<task>/`, never in an atom task. The atom tasks of one task are scored together against them.

## Fingerprint

A task's fingerprint is the SHA-256 over every file in its folder, in path order, each file's relative path followed by its bytes, excluding `FINGERPRINT` itself. It is written to the folder's `FINGERPRINT` file. `medomni bench task check` recomputes it and fails if it differs.

## Batches

A batch pins task ids to fingerprints, in `bench/tasks/batches/<name>.yaml`.

| Batch | Data | Tasks |
|---|---|---|
| `smoke-dummy` | Dummy data | One per task, on generated data. |
| `vitaldb` | VitalDB | The VitalDB tasks. |
| `v1-mini` | AI-READI, MIMIC-IV, BDSP | The 30 `-mini` tasks. |
| `v1-full` | AI-READI, MIMIC-IV, BDSP | Every task and its `-mini` and `-full` specs. |

## Where next

- [Families](families.md): the inputs a spec can name.
- [Contribute](../guides/contribute.md): write a new spec.
- [Datasets](datasets.md): what each dataset needs.
