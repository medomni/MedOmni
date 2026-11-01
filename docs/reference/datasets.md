# Datasets

Every dataset v0.3.0 builds tasks from, with how to get access and what its policy allows.

Contract: dataset policy, `src/medomni/core/contracts/schemas/dataset-policy.schema.json`. Each dataset has one adapter and one policy, in `src/medomni/bench/datasets/<dataset>/`.

!!! note "Not legal advice"
    Each policy summarises the data owner's license and data use agreement. `medomni bench run` enforces the route rules. You are responsible for the rest of your agreement.

## Datasets in v0.3.0

| Dataset | Access | License | What may be published | Routes |
|---|---|---|---|---|
| **MIMIC-IV 3.1** (core, ED, CXR-JPG, Note 2.2) | Credentialed (PhysioNet) | PhysioNet Credentialed Health Data License 1.5.0 + DUA | Schema, specs, cohort rules, seeds, fingerprints, aggregate results. Never labels or per-record outputs | `local`. `cloud` only with verified zero retention, no training and no human review |
| **MIMIC-IV-ECG 1.0, MIMIC-IV Waveform 0.1.0** | Open (PhysioNet) | ODbL 1.0 | Schema, specs, IDs, samples, with attribution and share-alike | `local`, `cloud` |
| **AI-READI** | Credentialed (FAIRhub) | AI-READI Data License Agreement v2.0; type 2 diabetes research only | Schema, specs, cohort rules, seeds, fingerprints, a small representative sample in papers. Never labels, ID lists or derived data | `local`. `cloud` only with a HIPAA BAA between the vendor and your institution; never for model training |
| **BDSP Human Sleep Project** | Credentialed (bdsp.io) | BDSP Credentialed Health Data License 1.5.0 + DUA | Schema, specs, cohort rules as a selection rule plus a hash, fingerprints. Never record-level derivatives | `local` only, unless BDSP approves otherwise in writing |
| **VitalDB** (PhysioNet copy) | Open (PhysioNet) | CC BY 4.0 | Everything, with attribution | `local`, `cloud` |
| **Dummy data** | Generated | None | Everything | `local`, `cloud` |

## Policy file

| Field | Required | Meaning |
|---|---|---|
| `dataset` | yes | Dataset id, matching its adapter: `mimic-iv`, `aireadi`, `bdsp`, `vitaldb`, `dummy`. |
| `version` | yes | The dataset release the policy was read against. |
| `access` | yes | `open` or `credentialed`. |
| `license` | yes | `id` and `url` of the license or data use agreement. |
| `modules` | no | Per-module overrides where modules carry different licenses. |
| `publish` | yes | For each kind of output (`schema`, `task_specs`, `id_lists`, `labels`, `per_record_derived`, `samples`): `allow`, `conditional` or `deny`. |
| `routes` | yes | `local` and `cloud`, each `allow`, `conditional` or `deny`. |
| `route_conditions` | no | What a `conditional` route requires, such as verified zero retention. |
| `use` | yes | Whether commercial use is allowed, and any restriction on purpose. |
| `attribution` | no | The notice a published sample must carry. |
| `sources` | yes | The license, agreement and FAQ pages the policy was read from. |

## Rules

- `medomni bench run` refuses a route the policy marks `deny`, and asks you to confirm each condition of a `conditional` route.
- Nothing marked `deny` under `publish` is ever uploaded or published. For credentialed datasets, a rebuild recipe (spec plus fingerprint) ships instead of data.
- A task sample on Hugging Face is allowed only where `publish.samples` is `allow`.

## Where next

- [Connect your data](../guides/connect-your-data.md): build tasks from your own access.
- [Tasks](tasks.md): the tasks and task suites on each dataset.
- [Design principles](../learn/principles.md): why patient data stays local.
