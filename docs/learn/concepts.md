# Concepts

Each term below has one meaning across the MedOmni code and docs.

| Term | What it is |
|---|---|
| **Dataset** | A source of patient data obtained under its own license: MIMIC-IV, AI-READI, BDSP, VitalDB. MedOmni never ships one. |
| **Dataset adapter** | The plug-in that finds a dataset on disk, surveys it into a catalog and extracts the files a task needs. |
| **Dataset policy** | One file per dataset, taken from its license, saying what may be published and which model routes may see its data. |
| **Family** | A kind of input that one encoder can read, defined by a protocol (format, channels, sampling rate, units) plus aliases. Datasets and encoders share families; neither owns them. |
| **Dummy data** | Data generated from a family's protocol alone, never from a record, so every task type runs with no credentials. |
| **Task spec** | The frozen question: what is asked, which evidence is allowed, how the answer is judged, and which cohort it binds to. A spec sets a mode: `selected` (curated evidence), `full` (the dataset's whole surface minus leakage) or `mini` (a small cohort). |
| **Task** | The folder a spec emits: instruction, environment, tests and a fingerprint. The same spec on the same data gives the same bytes. |
| **Atom task** | One task for one patient. It is the unit an agent runs and the unit of cost. |
| **Fingerprint** | The hash of a task's content. Publishing it lets anyone rebuild the task and prove it matches. |
| **Batch** | A pinned, append-only list of task fingerprints, such as `v1-mini`. A published score cites a batch. |
| **Encoder** | A containerised model or rule that turns one family's input into evidence an agent can read. |
| **Card** | An encoder's declared facts: provenance, inputs and outputs, license, reliability, known limits. It is written once, never computed at request time. |
| **Gateway** | The HTTP service an agent calls to reach encoders: `list_encoders`, `get_card`, `encode`. |
| **Agent** | The system under test: a model, a scaffold and a route, brought by the model tester as a config. The route says where the model runs (local or a named cloud service) and is checked against each dataset policy. |
| **Run** | One atom task done by one agent once. Every run writes one ledger row; the verifier, fixed per task, scores the runs of a task together. |

## Where next

- [Constitution](constitution.md): the rules every part of MedOmni follows.
- [Architecture](architecture.md): where each concept lives.
- [Contracts](contracts/index.md): the schemas behind families, tasks, cards and ledger rows.
