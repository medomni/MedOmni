# Concepts

Each term below has one meaning across the MedOmni code and docs.

| Term | What it is |
|---|---|
| **Dataset** | A source of patient data obtained under its own license. v0.2.0 supports MIMIC-IV, AI-READI and BDSP. MedOmni never ships one. |
| **Adapter** | The code that reads one dataset from disk for the task builder: `data_task/taskbuilder/adapters/{mimic,aireadi,bdsp}.py`. |
| **Family** | A kind of input that one encoder can read, defined by a protocol (format, channels, sampling rate, units) plus aliases. Datasets and encoders share families; neither owns them. |
| **Task spec** | The frozen question: what is asked, which evidence is allowed, how the answer is judged, and which cohort it binds to. One yaml in `data_task/taskbuilder/specs/`. A spec without a suffix is a task type; `-full` and `-mini` specs are its whole-record and small-cohort versions. |
| **Task** | The folder a spec emits: instruction, environment, tests and a fingerprint. The same spec on the same data gives the same bytes. |
| **Atom task** | One task for one patient, built from a task type by the atomic builder. It is the unit an agent runs and the unit of cost. Its parent holds the cohort, the gold answers and the fingerprint. |
| **Variant** | Which version of an atom the agent gets. `enc` has the encoder sidecar, `noenc` has none, `enc-forced` requires at least one encoder call, `ladder` adds modalities rung by rung. The variants differ only in encoder access. |
| **Generation** | A label for one build of the atom tasks, such as `fix-smoke`. An experiment names the generation it runs, and the harness checks it. |
| **Fingerprint** | The hash of a task's content. Anyone with the same data can rebuild the task and prove it matches. |
| **Batch** | A pinned list of task fingerprints, such as `v1-mini`. |
| **Encoder** | A containerised model or rule that turns one family's input into evidence an agent can read. |
| **Card** | An encoder's declared facts: provenance, inputs and outputs, license, reliability, known limits. It is written once, never computed at request time. |
| **Gateway** | The HTTP service an agent calls to reach encoders: `list_encoders`, `get_card`, `encode`. Inside a task it runs as the perception sidecar. |
| **Agent** | The system under test: a Harbor agent (the scaffold, `terminus-2` in v0.2.0) plus a model, declared in `harness/harbor/agents/<name>.yaml`. |
| **Experiment** | One yaml in `harness/experiments/` declaring agents × variants × repetitions over a generation's task types. Each cell of that grid is one Harbor job. |
| **Run** | One atom task done by one agent once. Every run writes an atom row to the ledger; the scorer scores the runs of one task type together and writes a cell row. |

## Where next

- [Constitution](constitution.md): the rules every part of MedOmni follows.
- [Architecture](architecture.md): where each concept lives.
- [Contracts](contracts/index.md): the schemas behind families, tasks, cards and ledger rows.
