# MedOmni

MedOmni is open-source software for medical AI on many data modalities: tables, waveforms, images and notes.

!!! info "This is v0.3.0, the first public release"
    MedOmni v0.3.0 (git tag `v0.3.0`) is the first public release and the first milestone of MedOmni. It has:

    - the `medomni` package and command
    - versioned contracts shared by all projects
    - four extension points (agent, dataset adapter, task, encoder), filled by pull request or plug-in package without changing Core

!!! warning "No patient data ships with MedOmni"
    The repository holds code, contracts and task specs. Data comes from:

    - generated dummy data
    - open datasets, such as VitalDB
    - datasets you are licensed to use, such as MIMIC-IV

## What v0.3.0 includes

Two projects and the core they share:

| Project | Does | Package | Command |
|---|---|---|---|
| **Bench** | Runs AI agents on medical tasks and scores them. A task gives an agent one patient's evidence and a clinical question; a fixed verifier scores the answer. It scores the agent as a whole (scaffold and model), as Terminal-Bench and SWE-bench do. | `medomni.bench` | `medomni bench` |
| **Perception** | Serves 44 medical encoders through an HTTP gateway. Each encoder reads one kind of input, such as a 12-lead ECG, and returns evidence for an agent or your own code. | `medomni.perception` | `medomni perception` |
| **Core** | Shared by both projects: the contracts, the `medomni` command, plug-in loading, the testing kit and the audit. | `medomni.core` | `medomni` |

Not in v0.3.0: MedOmni Agent (a later project) and a PyPI release.

## Who it is for

| Project | You are | You want to | Start here |
|---|---|---|---|
| Bench | **Agent evaluator** | Run your agent on MedOmni tasks and read the scores | [Run your agent](guides/run-your-agent.md) |
| Perception | **Encoder user** | Call medical encoders over HTTP from your own code | [Use the encoders](guides/use-the-encoders.md) |
| Bench or Perception | **Contributor** | Add an agent, a dataset adapter or a task to Bench, or an encoder to Perception | [Contribute](guides/contribute.md) |

## How it fits together

Bench and Perception each have their own package and content folder, and depend only on Core. Inside a task, Bench's sidecar calls Perception's gateway through the Gateway API. Tasks, traces and results stay on your machine. [Architecture](learn/architecture.md) shows the layout.

## Where next

- [Get started](get-started.md): install and score a first run on dummy data.
- [Design principles](learn/principles.md): how MedOmni treats data, tasks and contributions, and where its design comes from.
- [Concepts](learn/concepts.md): the terms used across these docs.
- [Architecture](learn/architecture.md): the repository layout and how the projects fit.
