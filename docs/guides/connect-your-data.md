# Connect your data

This guide is for agent evaluators with access to a credentialed dataset: you end up with MedOmni tasks built from your own copy.

## Before you start

- Access granted by the data owner, under its license: PhysioNet credentialing for MIMIC-IV, the AI-READI data license, the BDSP data use agreement. MedOmni cannot grant or check access for you.
- A local copy of the dataset. Read its row in [Datasets](../reference/datasets.md) for what its license permits.

## Steps

1. Tell the task builder where each dataset is, in `data_task/data_roots.yaml`:

    ```yaml
    mimic: /path/to/mimic-iv
    aireadi: /path/to/aireadi
    bdsp: /path/to/bdsp
    ```

2. Build atom tasks for the task types and conditions you want. `-n` is the number of patients per type; `--seed` fixes which ones.

    ```bash
    python data_task/taskbuilder/emit_atomic.py --all --variant enc --batch smoke -n 2
    ```

3. To rebuild a pinned spec task instead, emit it from its spec and validate it.

    ```bash
    python data_task/taskbuilder/emit.py data_task/taskbuilder/specs/mimic_icu-stay-radiology-mini.yaml
    ```

    ```bash
    python data_task/taskbuilder/validate.py data_task/taskbuilder/specs/mimic_icu-stay-radiology-mini.yaml
    ```

4. Compare the fingerprint in `data_task/tasks/<task-id>/FINGERPRINT` with the task's entry in `data_task/tasks/batches/v1-mini.yaml`.

## Check

`validate.py` prints a JSON report and exits 1 on any failure: a missing key, a metric outside the vocabulary, a leaking input, answers under `data/`, or a folder that no longer matches its `FINGERPRINT`. A fingerprint that differs from the batch's means your copy (version, missing module) or the build differs; do not compare scores across the two.

!!! warning "Keep data local"
    Built tasks, answers, traces and the results file all contain patient data. Never commit, upload or share them, and only send a task to a model provider the dataset's license allows (see [Datasets](../reference/datasets.md)).

## Where next

- [Tasks](../reference/tasks.md): what a built task contains, how its fingerprint is computed, and the pinned batches.
