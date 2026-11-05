# Connect your data

For agent evaluators with access to a credentialed dataset. You tell MedOmni where your copy is, check that it is the version the dataset package describes, and build its cache.

## Before you start

- Access granted by the data owner, under its license: PhysioNet credentialing for MIMIC-IV, the AI-READI data license, the BDSP data use agreement. MedOmni cannot grant or check access for you.
- A local copy of the dataset. Read its row in [Datasets](../reference/datasets.md) for what its license permits and which parts you need.
- For BDSP, which you download in parts: the list of files to download.

    ```bash
    medomni studio download-list bdsp
    ```

## Steps

1. Tell MedOmni where your copy is. The path is recorded in your workspace config.

    ```bash
    medomni bench data connect mimic-iv --path /path/to/mimic-iv
    ```

2. Check your copy. This loads the dataset up to the event table, without building any task: the version, the files the package lists, and the tables it reads.

    ```bash
    medomni bench data check mimic-iv
    ```

3. Build the dataset's cache: its event table and file conversions.

    ```bash
    medomni cache build mimic-iv
    ```

## Check

`medomni bench data check` names each problem it finds and exits 1:

- a version that differs from the one the package describes
- a file the package lists that is missing
- a table or column the format readers need that is missing

Fix your copy and run it again. When it passes, build a task set as in [Rebuild a task set](rebuild-a-task-set.md).

!!! warning "Keep data local"
    The cache, built atom tasks, answers, traces and the results file contain patient data. Do not commit, upload or share them.

## Where next

- [Rebuild a task set](rebuild-a-task-set.md): build a published task set and check its fingerprints.
- [Datasets](../learn/bench/datasets.md): the dataset package and the event table.
