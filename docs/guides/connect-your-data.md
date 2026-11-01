# Connect your data

For agent evaluators with access to a credentialed dataset. You build a published batch from your own copy and check it against the published fingerprints.

## Before you start

- Access granted by the data owner, under its license: PhysioNet credentialing for MIMIC-IV, the AI-READI data license, the BDSP data use agreement. MedOmni cannot grant or check access for you.
- A local copy of the dataset. Read its row in [Datasets](../reference/datasets.md) for what its license permits.

## Steps

1. Tell MedOmni where your copy is. The path is recorded in your workspace configuration.

    ```bash
    medomni bench data connect mimic-iv --path /path/to/mimic-iv
    ```

2. Build the batch. The dataset adapter surveys your copy, and each task spec builds its tasks and atom tasks in the workspace.

    ```bash
    medomni bench task build --batch v1-mini
    ```

3. Check the build against the batch's published fingerprints.

    ```bash
    medomni bench task check --batch v1-mini
    ```

## Check

`medomni bench task check` reports each task as matching or not matching its published fingerprint, and exits 1 on any mismatch. A mismatch means your copy or build differs, for example a different version or a missing module. Do not compare its scores with published ones.

!!! warning "Keep data local"
    Built tasks, answers, traces and the results file contain patient data. Do not commit, upload or share them.

## Where next

- [Tasks](../reference/tasks.md): what a built task contains, how its fingerprint is computed, and the published batches.
- [Run your agent](run-your-agent.md): run on the batch you built.
