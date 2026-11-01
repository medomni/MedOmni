# Datasets

A dataset is a source of patient data used under its own license. Bench reads it through a dataset adapter and obeys its dataset policy. MedOmni ships no data.

```text
your copy ──adapter──▶ files in families ──task builder──▶ atom tasks
                 policy ──▶ which routes may see them
```

## Dataset adapter

One adapter per dataset. It is the only dataset-specific code in Bench: every later step of the [task pipeline](tasks.md#task-pipeline) is shared. It:

- finds the dataset on disk, at the path you gave with `medomni bench data connect`
- surveys what each patient has: which families, at which times
- extracts the files a task needs, in its family's format

!!! warning "Designed later in Stage 1"
    The adapter's methods are designed with the task pipeline, from probes of MIMIC-IV, AI-READI, BDSP and VitalDB.

## Family bridge

Some datasets store recordings in a format no family uses, such as BDSP's HDF5 files. The family bridge converts each recording into its family's format once, and keeps the result in a cache in the workspace. The cache key covers the source file, the family, the family's declaration and aliases, and the bridge version. A change to any of them converts again.

## Dataset policy

One policy per dataset, read from its license and data use agreement. It records:

- what may be published: schema, specs, ID lists, labels, per-record outputs, samples
- which model routes may see the data: `local`, `cloud`, or `cloud` under conditions
- any limits on use, such as research only

`medomni bench run` refuses a route the policy does not allow. Nothing the policy denies is published.

## Open, credentialed and dummy data

| Kind | Examples | What you need |
|---|---|---|
| Credentialed | MIMIC-IV, AI-READI, BDSP | Your own access. MedOmni publishes fingerprints, never data. |
| Open | VitalDB | Nothing. Task samples are on Hugging Face. |
| Dummy | Generated | Nothing. Made from each family's declared format, never from a real record. |

Dummy data lets every command run with no credentials. Its scores only show that the pipeline works.

## Where it lives

- `src/medomni/bench/datasets/<dataset>/`: the adapter and the policy
- `src/medomni/bench/datasets/dummy/`: the dummy-data generator
- your workspace: the path to your copy, and the bridge cache

## Where next

- [Datasets reference](../../reference/datasets.md): every dataset, its license and its policy fields.
- [Connect your data](../../guides/connect-your-data.md): build tasks from your own copy.
- [Tasks](tasks.md): what the extracted files become.
