# Connect your data

This guide is for model testers who hold access to a credentialed dataset: you end up with the tasks of a published batch built on your machine and proven identical to everyone else's.

!!! note "Draft"
    The dataset adapter interface arrives in v1.0.0 (roadmap phase 4).

## Before you start

- Access granted by the data owner, under its license: PhysioNet credentialing for MIMIC-IV, the AI-READI data license, the BDSP data use agreement. MedOmni cannot grant or check access for you.
- A local copy of the dataset, on storage the license allows. Read the dataset's row in [Datasets](../catalog/datasets.md) for what its license permits.

## Steps

1. Tell MedOmni where the dataset is.

    ```bash
    medomni data connect mimic-iv --path /path/to/your/copy
    ```

2. Build the batch. The dataset adapter surveys your copy into a catalog, then each task spec emits its task folders locally.

    ```bash
    medomni task build --batch v1-mini
    ```

3. Verify the build against the published fingerprints.

    ```bash
    medomni task check --batch v1-mini
    ```

4. Run your agent on the batch, as in [Run your agent](run-your-agent.md).

## Check

`medomni task check` reports every task as matching or not matching its published fingerprint. A mismatch means your copy differs (version, missing module) or the build did; do not report scores from a mismatched task.

!!! warning "Keep data local"
    Built tasks contain patient data. Never upload them, share them, or send them to a model route the dataset policy does not allow.

## Where next

- [Fingerprint](../learn/contracts/fingerprint.md): how the match is computed.
- [Dataset policy](../learn/contracts/dataset-policy.md): what each policy controls.
- [Benchmarks](../catalog/benchmarks.md): the batches you can build.
