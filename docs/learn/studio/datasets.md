# Datasets

A dataset is a source of patient data used under its own license. Bench reads it through a dataset adapter and obeys its dataset policy. MedOmni ships no data.

```text
your copy ──adapter──▶ files in families ──task builder──▶ atom tasks
                 policy ──▶ which routes may see them
```

## Dataset adapter

One adapter per dataset. It:

- finds the dataset on disk, at the path you gave with `medomni bench data connect`
- surveys what each patient has: which families, at which times
- extracts the files a task needs, in its family's format

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

- `bench/datasets/<dataset>/`: the adapter and the policy
- `bench/datasets/dummy/`: the dummy-data generator
- your workspace: the path to your copy

## Where next

- [Datasets reference](../../reference/datasets.md): every dataset, its license and its policy fields.
- [Connect your data](../../guides/connect-your-data.md): build tasks from your own copy.
- [Tasks](tasks.md): what the extracted files become.
