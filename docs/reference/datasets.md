# Datasets

Every dataset v0.3.0 builds tasks from, with how to get access and what its policy allows, and the fields of a dataset package.

Contracts: dataset config, `dataset-config.schema.json`, and dataset policy, `dataset-policy.schema.json`, in `src/medomni/core/contracts/schemas/`. Each dataset has one package, in `bench/datasets/<dataset>/`.

!!! note "Not legal advice"
    Each policy summarises the data owner's license and data use agreement. `medomni bench run` enforces the route rules. You are responsible for the rest of your agreement.

## Datasets in v0.3.0

| Dataset | Access | License | What may be published | Routes |
|---|---|---|---|---|
| **MIMIC-IV 3.1** (core, ED, CXR-JPG, Note 2.2) | Credentialed (PhysioNet) | PhysioNet Credentialed Health Data License 1.5.0 + DUA | Schema, templates, recipes, fingerprints, aggregate results. Never labels or per-record outputs | `local`. `cloud` only with verified zero retention, no training and no human review |
| **MIMIC-IV-ECG 1.0, MIMIC-IV Waveform 0.1.0** | Open (PhysioNet) | ODbL 1.0 | Schema, templates, recipes, IDs, samples, with attribution and share-alike | `local`, `cloud` |
| **AI-READI** | Credentialed (FAIRhub) | AI-READI Data License Agreement v2.0; type 2 diabetes research only | Schema, templates, recipes, fingerprints, a small representative sample in papers. Never labels, ID lists or derived data | `local`. `cloud` only with a HIPAA BAA between the vendor and your institution; never for model training |
| **BDSP Human Sleep Project** | Credentialed (bdsp.io) | BDSP Credentialed Health Data License 1.5.0 + DUA | Schema, templates, recipes (a selection rule plus a hash), fingerprints. Never record-level derivatives | `local` only, unless BDSP approves otherwise in writing |
| **VitalDB** (PhysioNet copy) | Open (PhysioNet) | CC BY 4.0 | Everything, with attribution | `local`, `cloud` |
| **Dummy data** | Generated | None | Everything | `local`, `cloud` |

## Universes

Each cohort draws from its dataset's universe: the patients for whom `sha256(salt|patient id)`, read as a fraction, is below the default fraction. A cohort may set a smaller fraction.

| Dataset | Unit | Default universe |
|---|---|---|
| MIMIC-IV | Patient | 5% of patients |
| AI-READI | Participant | All |
| BDSP | Patient at site I0006 | 10% of patients; download only their latest sleep study, listed by `medomni toolkit download-list bdsp` |
| VitalDB | Surgery case | All |

## Dataset package

| File | Required | Holds |
|---|---|---|
| `dataset.yaml` | yes | The dataset config, below. |
| `labels.yaml` | yes | The label library. See [Recipes](recipes.md#label-library). |
| `evidence.yaml` | yes | The evidence rules. See [Recipes](recipes.md#evidence-file). |
| `codes.csv` | yes | Every code the dataset emits: `code`, `description`, `source_table`. |
| `policy.yaml` | yes | The dataset policy, below. |
| `hooks/` | no | Python for labels or rules no config can express. |
| `tasks/` | no | Task templates and their cohorts. |

`dataset.yaml`:

| Field | Required | Meaning |
|---|---|---|
| `description` | yes | `unit` (what one subject is), `time` (the kind of time: date and time, visit dates only, seconds from start) and `version` (the dataset release). |
| `units` | yes | The table and column that list every subject. |
| `universe` | yes | `salt` and the default `fraction`, or `all`. |
| `verify` | no | What to check before reading: files listed in manifests, one file per unit, the dataset's own checksums. |
| `read` | yes | A list of readers, each with what it reads: tables and columns, the code to emit, folder patterns per family. |
| `rules` | no | Timing and visit rules, such as one visit per participant or times in seconds from case start. |
| `conditions` | no | Named conditions that recipes use. See [Recipes](recipes.md#cohort-file). |

## Policy file

| Field | Required | Meaning |
|---|---|---|
| `dataset` | yes | Dataset id, matching its package folder: `mimic-iv`, `aireadi`, `bdsp`, `vitaldb`, `dummy`. |
| `version` | yes | The dataset release the policy was read against. |
| `access` | yes | `open` or `credentialed`. |
| `license` | yes | `id` and `url` of the license or data use agreement. |
| `modules` | no | Per-module overrides where modules carry different licenses. |
| `publish` | yes | For each kind of output (`schema`, `templates`, `recipes`, `id_lists`, `labels`, `per_record_derived`, `samples`): `allow`, `conditional` or `deny`. |
| `routes` | yes | `local` and `cloud`, each `allow`, `conditional` or `deny`. |
| `route_conditions` | no | What a `conditional` route requires, such as verified zero retention. |
| `use` | yes | Whether commercial use is allowed, and any restriction on purpose. |
| `attribution` | no | The notice a published sample must carry. |
| `sources` | yes | The license, agreement and FAQ pages the policy was read from. |

## Rules

- `medomni bench run` refuses a route the policy marks `deny`, and asks you to confirm each condition of a `conditional` route.
- Nothing marked `deny` under `publish` is ever uploaded or published. For credentialed datasets, templates, recipes, fingerprints and hashes ship instead of data.
- A task sample on Hugging Face is allowed only where `publish.samples` is `allow`.

## Where next

- [Connect your data](../guides/connect-your-data.md): build tasks from your own access.
- [Tasks](tasks.md): the templates and task sets on each dataset.
- [Recipes](recipes.md): the label library and evidence files in each package.
- [Design principles](../learn/principles.md): why patient data stays local.
