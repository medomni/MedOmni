# Datasets

Every dataset this version supports, with how to get access and what its license lets MedOmni publish and send to a model.

!!! note "Draft"
    The license readings below were checked on 2026-10-18 against each data owner's license, data use agreement or FAQ. They are a reading of the terms, not legal advice; the dataset policy files are the binding form. The VitalDB adapter and the dummy-data generator arrive in roadmap phase 4.

| Dataset | Access | Adapter | License | What may be published | LLM routes |
|---|---|---|---|---|---|
| **Dummy data** | None: generated from family protocols | `medomni.datasets.dummy` | Apache-2.0 (generated) | Everything | Local and cloud |
| **VitalDB 1.0.0** (PhysioNet copy) | Open | `medomni.datasets.vitaldb` | CC BY 4.0 | Everything, with attribution | Local and cloud |
| **MIMIC-IV-ECG 1.0, MIMIC-IV Waveform 0.1.0** | Open | `medomni.datasets.mimic` | ODbL 1.0 | Schema, specs, IDs, samples, with attribution and share-alike | Local and cloud |
| **MIMIC-IV 3.1** (core, ED, CXR-JPG 2.1.0, Note 2.2) | Credentialed (PhysioNet) | `medomni.datasets.mimic` | PhysioNet Credentialed Health Data License 1.5.0 + DUA | Schema, specs, cohort rules, seeds, fingerprints, aggregate results. Never labels or per-record outputs | Local by default. Cloud only with verified zero retention, no training and no human review |
| **AI-READI** | Credentialed (FAIRhub) | `medomni.datasets.aireadi` | AI-READI Data License Agreement v2.0; type 2 diabetes research only | Schema, specs, cohort rules, seeds, fingerprints, a small representative sample in papers. Never labels, ID lists or derived data | Local by default. Cloud only with a HIPAA BAA between the vendor and your institution; never for model training |
| **BDSP Human Sleep Project** | Credentialed (bdsp.io) | `medomni.datasets.bdsp` | BDSP Credentialed Health Data License 1.5.0 + DUA | Schema, specs, cohort rules as a selection rule plus a hash, fingerprints. Never record-level derivatives | Local only, unless BDSP approves otherwise in writing |

Builder and harness code is always public: the MIMIC-IV and BDSP licenses require the code behind published results to be open.

## Where next

- [Dataset policy](../learn/contracts/dataset-policy.md): the fields each policy sets.
- [Connect your data](../guides/connect-your-data.md): build tasks from your own access.
- [Benchmarks](benchmarks.md): which batches use which datasets.
