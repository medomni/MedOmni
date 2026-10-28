# Architecture

MedOmni v0.2.0 in the [C4 model](https://c4model.com): who uses it (C1), its parts (C2), the components inside the harness (C3), the code inside the job builder (C4), and C1 to C3 nested in one picture.

## Context (C1)

![C1: MedOmni v0.2.0 in context](../assets/c1-context.drawio.svg)

- **Agent evaluator**: declares an experiment, runs it, reads the scores.
- **Encoder user**: calls the encoders through the gateway.
- **Contributor**: adds task specs, agent configs or encoders.
- **MedOmni**: one repository, run from a checkout. It builds tasks from raw data, runs agents on them and scores the runs.
- **Datasets**: MIMIC-IV, AI-READI and BDSP, read from local disk under the user's own license.
- **Model provider**: the API behind the agent's model, reached with the user's own key.
- **Harbor**: the agent-evaluation framework that runs each atom task in Docker.

## Containers (C2)

![C2: the repository's parts](../assets/c2-containers.drawio.svg)

| Part | Folder | Does |
|---|---|---|
| Data & Task | `data_task/` | Families, task specs, the task builder and batches. |
| Data manifest | `data_manifest/` | Which files exist for each patient, read by the task builder. |
| Perception | `perception/` | One container image per encoder, its model card, the registry that builds and tests them, and the gateway. |
| Harness | `harness/` | Experiments, the job builder, Harbor configs, the perception sidecar image, the scorer and the analysis tables. |
| Assurance | `assurance/` | [Audits](../reference/audit.md) of data, families, encoders, tasks and runs, each verdict bound to a fingerprint. |
| Runs | `runs/` | Traces and the results file. Local only; never committed. |

Inside one atom task, Harbor starts three containers on a closed network: the agent's workspace, a bootstrap step that stages the patient's files, and, when encoders are available, the perception sidecar, which runs the gateway and starts encoder containers on demand.

## Components of the harness (C3)

![C3: the components inside the harness](../assets/c3-components.drawio.svg)

| Component | Where | Does |
|---|---|---|
| Experiments | `harness/experiments/` | One yaml per experiment: agents, task types, conditions, repetitions. |
| Job builder | `harness/build.py` | `emit` turns an experiment into Harbor job overlays and prerun sheets; `import` turns finished trials into run records; `status` shows completeness. |
| Harbor configs | `harness/harbor/` | The base settings, one file per agent, and the generated job overlays that `harbor run` reads. |
| Perception sidecar | `harness/perception-image/` | The gateway inside each task, with a call budget and a call log. |
| Scorer | `harness/score.py`, `harness/metrics.py` | Scores each task type against its hidden answers; the only component that writes scores. |
| Analysis | `harness/analyze.py` | Turns scores into the experiment's task × agent × condition table. |

## Code of the job builder (C4)

![C4: the functions inside the job builder](../assets/c4-code-job-builder.drawio.svg)

`harness/build.py` has three commands and never scores. `emit` refuses to write jobs if a referenced file is missing or, in a scored experiment, an encoder in use is not runnable, and it copies the shared format check into each atom task's `tests/`. `import` records one run per trial and marks a run as an error when the served model differs from the experiment's declared one.

## All levels

![C1 to C3 nested: the system, its containers, and the harness components](../assets/c1-c3-overview.drawio.svg)

## Where next

- [Design principles](principles.md): the principles behind these parts.
- [Reference](../reference/tasks.md): the formats each part reads and writes.
- [Commands](../cli/index.md): every entry point.
