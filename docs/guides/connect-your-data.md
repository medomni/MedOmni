# Connect your data

For agent evaluators who build tasks on a real dataset. Every dataset is set up the same way, open or credentialed: get access, download your copy, tell MedOmni where it is, check it and build its cache. MedOmni hosts no dataset: you download each one from its owner.

## Before you start

- Access granted by the data owner, under its license: PhysioNet credentialing for MIMIC-IV, the AI-READI data license, the BDSP data use agreement. VitalDB is open and needs none. MedOmni cannot grant or check access for you.
- Read the dataset's row in [Datasets](../reference/datasets.md) for what its license permits.

## Steps

1. List what to download, then download it:

    ```bash
    medomni studio download-list mimic-iv
    ```

    It writes one tab-separated line per entry: the source, the path in your copy, and how to fetch it: `file`, `folder` (copied whole) or `gunzip` (decompressed on the way). The list is chosen from the dataset's index tables, so fetch those first: without them, it prints the index entries to download and stops.

    | Dataset | Source | What is listed |
    |---|---|---|
    | MIMIC-IV | PhysioNet | Core 3.1 and ED 2.2 whole; CXR-JPG 2.1.0, MIMIC-IV-ECG 1.0 and the Waveform Database 0.1.0 for the source population only. Their indexes are the CXR metadata and image list, the ECG `record_list.csv` and the waveform `RECORDS`. |
    | AI-READI | FAIRhub | Each participant's files, by the package's folder patterns. |
    | BDSP | BDSP's S3 access point | The index tables, then each source-population patient's latest night. About 349 listed scoring files are not on the server, because those nights were never scored, so a missing scoring file is expected. |
    | VitalDB | VitalDB's open API, `api.vitaldb.net` | The clinical, lab and track tables, then each case's `.vital` file. The package uses the API's file names, which differ from those of VitalDB's copy on PhysioNet. |

2. Tell MedOmni where your copy is. The path is recorded in your workspace config.

    ```bash
    medomni bench data connect mimic-iv --path /path/to/mimic-iv
    ```

3. Check your copy against the package, without loading it: the version, the files the package lists, the columns the readers need, and that every raw value a label reads is classified.

    ```bash
    medomni bench data check mimic-iv
    ```

4. Build the dataset's cache: its event table and file conversions.

    ```bash
    medomni cache build mimic-iv
    ```

## Check

`medomni bench data check` names each problem it finds and exits 1:

- a version that differs from the one the package describes
- a file the package lists that is missing
- a table or column the format readers need that is missing
- a raw value a label reads that the label library does not classify

Fix your copy and run it again. When it passes, build a task set as in [Rebuild a task set](rebuild-a-task-set.md).

!!! warning "Keep data local"
    The cache, built atom tasks, answers, traces and the results file contain patient data. Do not commit, upload or share them.

## Where next

- [Rebuild a task set](rebuild-a-task-set.md): build a published task set and check it.
- [Datasets](../learn/bench/datasets.md): the dataset package and the event table.
