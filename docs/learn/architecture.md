# Architecture

MedOmni v0.2.0 is shown here in three C4 views, from the outside in: who uses it, which containers it has, and which components do the work.

## Context (C1)

![C1: MedOmni v0.2.0 in context](../assets/c1-context.drawio.svg)

- **Model tester**: declares an experiment, runs it, reads the scores.
- **Perception service user**: calls the encoders through the gateway over HTTP.
- **Task or encoder author**: adds task specs, agent configs or encoders to the repository.
- **MedOmni**: one repository, run from a checkout. It builds tasks from raw data, runs agents on them and scores the runs.
- **Datasets**: MIMIC-IV, AI-READI and BDSP, read from local disk under each user's own license.
- **Model provider**: the API behind the agent's model (DeepSeek, OpenAI and others), reached with the user's own key.
- **Harbor**: the agent-evaluation framework that runs each atom task in Docker.
- **Hugging Face Hub**: private MedOmni datasets for family samples, tasks and encoder assets, for team members.

## Containers (C2)

![C2: the repository's parts](../assets/c2-containers.drawio.svg)

| Part | Folder | Does |
|---|---|---|
| Data & Task | `data_task/` | Families, task specs, the task builder (spec tasks and atom tasks), batches. |
| Data manifest | `data_manifest/` | The data plane the atomic builder reads: which files exist for each subject. |
| Perception | `perception/` | One container image per encoder, its card, the registry that builds and tests them, and the gateway. |
| Harness | `harness/` | Experiment declarations, the job builder, Harbor configs, the perception sidecar image, the scorer and the analysis tables. |
| Assurance | `assurance/` | The audit matrix: machine checks, LLM reviews and human sign-offs over families, tasks, encoders, the gateway and runs. |
| Runs | `runs/` | Every trace and the ledger. Local only; never committed. |
| Internal docs | `internal_docs/` | Roadmaps, design references and reports for the MedOmni team. |

Inside one atom task, Harbor starts three containers on a closed network: the agent's workspace (`main`), a `bootstrap` step that stages the patient's files, and, in the encoder variants, the `perception` sidecar. The sidecar runs the gateway and starts encoder containers on demand.

## Components (C3)

![C3: the components on the run path](../assets/c3-components.drawio.svg)

| Component | Where | Does |
|---|---|---|
| Family registry | `data_task/families/`, `data_task/family_alias.yaml` | Declares every input family and what it accepts. |
| Spec pipeline | `data_task/taskbuilder/intake/`, `emit.py`, `validate.py`, `push.py`, `pin_batch.py` | Turns a proposal into a frozen spec, a task folder, a fingerprint and a batch entry. |
| Atomic builder | `data_task/taskbuilder/emit_atomic.py` | Builds one atom per task type and patient, in each variant, with the parent's cohort, gold and fingerprint. |
| Encoder registry | `perception/registry.py`, `perception/encoders.yaml` | Validates cards, builds images, tests them against expected responses, reports status. |
| Gateway | `perception/gateway/` | Serves `list_encoders`, `get_card` and `encode`, and manages a pool of encoder containers. |
| Perception sidecar | `harness/perception-image/` | The gateway inside a task: call budget, scoped catalogue, and a call log for scoring. |
| Job builder | `harness/build.py` | `emit` turns an experiment into Harbor jobs and a prerun sheet; `import` writes atom rows; `status` shows completeness. |
| Scorer | `harness/score.py`, `harness/metrics.py` | The only thing that writes scores: one cell row per task type, condition and repetition. |
| Analysis | `harness/analyze.py` | Turns the ledger into the experiment's task × model × variant table. |
| Audit matrix | `assurance/audit_matrix_v2/` | Records verdicts bound to fingerprints; a verdict goes stale when its subject changes. |

## Where next

- [Contracts](contracts/index.md): the interfaces between the parts.
- [Code map](../api/index.md): every folder and its entry points.
- [Concepts](concepts.md): the terms used above.
