# Built tasks

A built task is what a task builder writes and what Bench runs and scores. Its files follow one contract, so Bench runs a built task whoever built it. MedOmni's own builder, `medomni-v1`, is in [Studio](../studio/build.md); a plug-in package can add another.

```text
builder ──writes──▶ built task: content + atom tasks ──Bench checks, runs and scores──▶ results
```

## The files

A built task is one content folder and one atom task per patient under each arm, in the workspace's built-task folder:

```text
atomtasks/
├── _content/<task>/
│   ├── content.json       version, targets (name, metric), atoms (atom, subject, prediction time)
│   ├── answers.csv        each patient's answer for every target: subject_id, target, value, metric
│   └── manifest.json      config_hash (one per arm and variant), builder (<name>/<version>)
└── <arm>/[<variant>/]<atom>/
    ├── task.toml          the atom's metadata: task, patient, arm, variant, prediction time, resources
    ├── instruction.md     what the agent reads first
    ├── data/              the patient's staged files
    ├── environment/       the closed-network containers: docker-compose.yaml, Dockerfile
    └── tests/
        ├── expected.json  the target names
        ├── format_check.py
        └── test.sh
```

- Bench's runner and scorer read `content.json`, `answers.csv` and `manifest.json`, and each atom's `tests/expected.json` and `tests/format_check.py`. Harbor reads the rest of the atom.
- The contract names only the fields Bench reads. A builder may add its own fields to `content.json` and `manifest.json`, such as `medomni-v1`'s step counts and release.
- The runner finds an arm's variants in the keys of `manifest.json`'s `config_hash`, such as `modality-ladder/r1`.
- `answers.csv` stays in the content folder. No atom task holds it.
- Core supplies the atom's shared Harbor parts, the agent's `Dockerfile`, `bootstrap.sh`, `format_check.py` and `test.sh`, so every builder stages the same ones.

A builder may write more files of its own, such as `medomni-v1`'s `record.json` for each patient. Bench never reads them.

## Checks on any built task

Bench runs these on the whole task set before every run, whoever built it. If any fails, nothing runs. MedOmni's builder runs them too, right after it writes.

- **Files present:** the content folder and every atom task hold the contract's files, and their fields follow it.
- **No answers in an atom task:** no atom folder holds `answers.csv`, `content.json` or a patient's `record.json`.
- **Format check works:** each atom's `format_check.py` accepts a well-formed submission.
- **Nothing after the prediction time:** every staged file the builder dated, in the atom's `data/references.jsonl`, is dated at or before the prediction time in `task.toml`.
- **Complete recordings:** every staged WFDB header comes with its signal files and segments. This check reads your copy of the data.
- **Closed network:** every container of an atom task is on one internal network, with no route out.

The checks that need the recipe or the source data, such as no answer in the evidence, belong to the builder. See [Build](../studio/build.md#correctness-checks) for `medomni-v1`'s.

## Arms

An arm is one name, registered in `medomni.arms`. Its two sides are apart:

- **Build side:** what the arm hides or shows in the atom task, such as the instruction paragraph, the staged files or the ladder's masks. Each builder implements it for the arms it supports, and refuses an arm it doesn't support.
- **Run side:** what the run attaches, such as the perception service and its call budget. Bench implements it.

An arm from a plug-in package registers its run side in `medomni.arms` and its build side for each builder in `medomni.arm_builds`, named `<builder>:<arm>`, such as `medomni-v1:my-arm`. See [Arms](../bench/runs.md#arms).

## Write your own builder

A builder is a subclass of `TaskBuilder`, registered in the `medomni.builders` entry-point group:

| Member | Is |
|---|---|
| `name` | The builder's registered name, such as `medomni-v1`. |
| `version` | The builder's version. It goes into every config hash the builder writes. |
| `config_files(task, arm, variant)` | What the task's config hash covers under that arm and variant: files, or bytes, by name. |
| `build(tasks, arms, workspace)` | Writes each task's content folder and its atom tasks under each arm in the layout above, and returns the content folders. It refuses, naming the task, anything it cannot build, such as an arm it doesn't support. |

The task id is a string the builder understands; for `medomni-v1` it is `<template>@<cohort>`. Core knows nothing of recipes, templates or cohorts.

A task set names its builder in its `builder` field, and `medomni studio task build --set <set>` builds it with that builder.

MedOmni's tests build a dummy set with a builder from a test package, then run it with the replay agent and score it. A builder whose output passes the checks above runs in Bench the same way.

## Where it lives

- `src/medomni/core/contracts/built.py`: the built-task files, as models
- `src/medomni/core/tasks/`: the atom layout, task sets, the checks on built tasks and the atom's shared Harbor parts
- `src/medomni/core/builders.py`: `TaskBuilder` and the `medomni.builders` group
- your workspace: the built tasks

## Where next

- [Build](../studio/build.md): MedOmni's builder, step by step.
- [Runs](../bench/runs.md): how Bench runs a built task.
- [Plug-ins](plugins.md): register a builder or an arm from a plug-in package.
