# Contribute

This guide is for task adders: you end up with a pull request that adds a task, a dataset adapter or an encoder, checked by CI.

All three share one route: copy a template, fill it in, run one check command locally, open a pull request, and CI runs the same check. Contributions touch only these extension points; contracts and the core are changed by the MedOmni team.

!!! note "Draft"
    Templates and CI checks arrive in v1.0.0 (roadmap phase 4). For now MedOmni accepts new tasks only with an openly licensed dataset, so no data-access question arises.

Every commit carries a DCO sign-off (`git commit -s`). Code is Apache-2.0; data samples keep their upstream license.

## Add a task

For tasks on a dataset and families MedOmni already supports.

### Before you start

- The dataset is openly licensed, or already supported with a policy that allows the task.
- The task's inputs map to existing families. See [Families](../learn/contracts/families.md).

### Steps

1. Create the spec from the template.

    ```bash
    medomni task new my-task --dataset vitaldb
    ```

2. Fill in the spec: the question, the target, the cohort rule, the prediction time, and the allowed evidence. Leakage bans derive from the target; do not list them by hand.
3. Build the task on dummy data and on the real dataset.
4. Upload a small data sample to the MedOmni task-samples repository on Hugging Face.
5. Open a pull request with the spec.

### Check

```bash
medomni task check specs/my-task.yaml
```

It validates the spec, builds the task, confirms no gold or leaking input reaches the agent, and recomputes the fingerprint.

## Add a dataset adapter

For a new openly licensed dataset, such as VitalDB.

### Before you start

- The dataset's license allows redistribution of samples (for example CC BY 4.0).
- You know which families its signals map to. If none fits, a new family is a contract change: open an issue first.

### Steps

1. Copy the template.

    ```bash
    cp -r templates/dataset medomni/datasets/my-dataset
    ```

2. Implement the adapter: locate the dataset, survey it into a catalog, and extract the files a task needs.
3. Write the dataset policy from the license: what may be published and which model routes are allowed.
4. Add at least one task on the dataset, as above.
5. Open a pull request.

### Check

```bash
medomni task check --dataset my-dataset
```

It runs the adapter against the data sample, validates the policy, and builds the dataset's tasks.

## Add an encoder

Encoders live in the encoder repository, not the main package.

### Before you start

- The encoder reads one existing family, and its weights have a license that allows redistribution.
- Test data for the family: synthetic or openly licensed, with a provenance note.

### Steps

1. Copy the template in the encoder repository.

    ```bash
    cp -r encoders/_template encoders/<family>/<encoder>
    ```

2. Write the encoder adapter, the Dockerfile and the card. The card declares input formats, span and windowing; nothing is discovered at run time.
3. Add test data and its provenance note.
4. Open a pull request in the encoder repository.

### Check

```bash
medomni encoder check encoders/<family>/<encoder>
```

It validates the card, builds the image, runs the encoder on the family's samples, and compares the evidence with the expected responses. GPU encoders may run on a self-hosted runner.

## Where next

- [Contracts](../learn/contracts/index.md): the interfaces your contribution must meet.
- [Constitution](../learn/constitution.md): the rules every task and encoder follows.
- [Datasets](../catalog/datasets.md): what each dataset's license allows.
