# Datasets

A dataset is a source of patient data used under its own license. Bench reads it through its dataset package and obeys its dataset policy. MedOmni ships no data.

```text
your copy ──readers + dataset package──▶ event table ──Build──▶ atom tasks
                         policy ──▶ which routes may see them
```

## Dataset package

One folder per dataset, `bench/datasets/<dataset>/`. It is configuration, not code:

- `dataset.yaml`: a description, the readers to use, the dataset's rules and its named conditions
- `labels.yaml`: the label library
- `evidence.yaml`: what an atom task may hold, relative to the prediction time
- `codes.csv`: every code the dataset emits, with a description and its source table
- `policy.yaml`: what the license allows
- `hooks/`: Python for what only this dataset needs, such as CKD staging by KDIGO
- `tasks/`: the dataset's task templates and their cohorts

The description states the unit (a patient, a participant, a surgery case), the kind of time (date and time, visit dates only, seconds from case start) and the dataset version. Time is described, not converted: Build refuses a recipe the dataset's time cannot support.

## Readers

Readers are shared code in Core, one per file format. A dataset package names the readers it uses and what they read; it does not repeat their code. v0.3.0 has readers for:

- CSV tables
- OMOP tables
- folder trees, where a file's folder gives its family
- recording headers: EDF, WFDB, HDF5 and DICOM

A dataset reads only the tables its recipes and labels use. A dataset in a format no reader knows adds a reader to Core, which every later dataset can use.

## Event table

Every dataset becomes one event table, kept in the [cache](../core/cache.md). It is the only thing later steps read.

| Column | Holds |
|---|---|
| `subject_id` | The unit: patient, participant or case |
| `time` | When the event happened; empty for static facts such as sex |
| `code` | What happened, such as `ADMISSION` or `LAB//cr` |
| `numeric_value`, `text_value` | The event's value, if any |
| `visit` | The visit the event belongs to |

- Column names follow [MEDS](https://github.com/Medical-Event-Data-Standard/meds), so MEDS tools can read the table.
- Raw files are `FILE//<family>` rows, with a path relative to your copy, and optionally a sha256 and the file's own id (a DICOM UID, a WFDB record).
- Annotations read from recordings, such as sleep stages, are events too.
- A few codes are shared by every dataset; the rest are the dataset's own. See [Shared codes](../../reference/recipes.md#shared-codes).

Raw files are never copied into the table or the cache. Only files a [family converter](../core/families.md#family-converters) changes are written to the cache.

## Dataset policy

One policy per dataset, read from its license and data use agreement. It records:

- what may be published: schema, templates, recipes, ID lists, labels, per-record outputs, samples
- which model routes may see the data: `local`, `cloud`, or `cloud` under conditions
- any limits on use, such as research only

`medomni bench run` refuses a route the policy does not allow. Nothing the policy denies is published. Recipes and fingerprints contain no patient data, so every policy allows them.

## Open, credentialed and dummy data

| Kind | Examples | What you need |
|---|---|---|
| Credentialed | MIMIC-IV, AI-READI, BDSP | Your own access. MedOmni publishes recipes, fingerprints and hashes, never data. |
| Open | VitalDB | Nothing. Task samples are on Hugging Face. |
| Dummy | Generated | Nothing. Made from each family's declared format, never from a real record. |

Dummy data lets every command run with no credentials. Its scores only show that the pipeline works. Every dataset package is also checked on dummy data, so its readers and rules run in CI.

## Where it lives

- `bench/datasets/<dataset>/`: the dataset package
- `src/medomni/core/readers/`: the readers
- `src/medomni/core/families/`: the family converters and the dummy-data generator
- your workspace: the path to your copy, and the cache

## Where next

- [Datasets reference](../../reference/datasets.md): every dataset, its license, and the package's fields.
- [Connect your data](../../guides/connect-your-data.md): connect and check your own copy.
- [Recipes](recipes.md): the queries that read the event table.
