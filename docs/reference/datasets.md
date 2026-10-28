# Datasets

Every dataset v0.2.0 builds tasks from, with how to get access and what its license lets you publish and send to a model provider.

!!! note "A reading, not legal advice"
    The readings below summarise each data owner's license and data use agreement. MedOmni does not enforce them in code: you are responsible for following your own agreement.

| Dataset | Access | Adapter | License | What may be published | Model providers |
|---|---|---|---|---|---|
| **MIMIC-IV 3.1** (core, ED, CXR-JPG, Note 2.2) | Credentialed (PhysioNet) | `adapters/mimic.py` | PhysioNet Credentialed Health Data License 1.5.0 + DUA | Schema, specs, cohort rules, seeds, fingerprints, aggregate results. Never labels or per-record outputs | Local by default. A cloud model only with verified zero retention, no training and no human review |
| **MIMIC-IV-ECG 1.0, MIMIC-IV Waveform 0.1.0** | Open (PhysioNet) | `adapters/mimic.py` | ODbL 1.0 | Schema, specs, IDs, samples, with attribution and share-alike | Local and cloud |
| **AI-READI** | Credentialed (FAIRhub) | `adapters/aireadi.py` | AI-READI Data License Agreement v2.0; type 2 diabetes research only | Schema, specs, cohort rules, seeds, fingerprints, a small representative sample in papers. Never labels, ID lists or derived data | Local by default. A cloud model only with a HIPAA BAA between the vendor and your institution; never for model training |
| **BDSP Human Sleep Project** | Credentialed (bdsp.io) | `adapters/bdsp.py` | BDSP Credentialed Health Data License 1.5.0 + DUA | Schema, specs, cohort rules as a selection rule plus a hash, fingerprints. Never record-level derivatives | Local only, unless BDSP approves otherwise in writing |

Adapters are in `data_task/taskbuilder/adapters/`, and each dataset's root on your machine is set in `data_task/data_roots.yaml`.

## Where next

- [Connect your data](../guides/connect-your-data.md): build tasks from your own access.
- [Tasks](tasks.md): the task types and batches on each dataset.
- [Design principles](../learn/principles.md): why patient data stays local.
