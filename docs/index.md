# MedOmni

MedOmni is open-source software for medical AI on many data modalities: tables, waveforms, images and notes.

MedOmni is developed in a private repository; the public repository is an export of each release, with every commit's author kept. Pull requests are reviewed and merged there and ship in the next release: see [How MedOmni is developed](guides/contribute.md#how-medomni-is-developed).

!!! info "This is v0.3.0, the first public release"
    MedOmni v0.3.0 (git tag `v0.3.0`) is the first public release and the first milestone of MedOmni. It has:

    - the `medomni` package and command
    - versioned contracts shared by all projects
    - four extension points (agent, dataset, task, encoder), filled by pull request or plug-in package without changing Core

!!! warning "No patient data ships with MedOmni"
    The repository holds code, contracts, dataset packages, templates and recipes. Data comes from:

    - generated dummy data
    - open datasets, such as VitalDB
    - datasets you are licensed to use, such as MIMIC-IV

## What v0.3.0 includes

Three projects and the core they share:

| Project | Does | Package | Command |
|---|---|---|---|
| **Bench** | Runs AI agents on built medical tasks and scores them, whoever built the tasks. A task gives an agent one patient's evidence and a clinical question; a fixed verifier scores the answer. It scores the agent as a whole (scaffold and model), as Terminal-Bench and SWE-bench do. | `medomni.bench` | `medomni bench` |
| **Perception** | Serves 44 medical encoders through an HTTP gateway. Each encoder reads one kind of input, such as a 12-lead ECG, and returns evidence for an agent or your own code. | `medomni.perception` | `medomni perception` |
| **Studio** | Makes and builds tasks: dataset survey, task proposals from clinicians, review and sign-off, cohort previews, MedOmni's task builder, the audit and reports. | `medomni.studio` | `medomni studio` |
| **Core** | Shared by every project: the contracts, the `medomni` command, plug-in loading, dataset loading, the family converter interface, the cache, the built-task contract and the testing kit. | `medomni.core` | `medomni` |

Not in v0.3.0: MedOmni Agent (a later project) and a PyPI release.

## Who it is for

| Project | You are | You want to | Start here |
|---|---|---|---|
| Bench | **Agent evaluator** | Run your agent on MedOmni tasks and read the scores | [Run your agent](guides/run-your-agent.md) |
| Perception | **Encoder user** | Call medical encoders over HTTP from your own code | [Use the encoders](guides/use-the-encoders.md) |
| Bench, Studio or Perception | **Contributor** | Add an agent to Bench, a dataset or a task to Studio, or an encoder to Perception | [Contribute](guides/contribute.md) |

## How it fits together

Bench and Perception each have their own package and content folder, and depend only on Core. Studio sits above both: its builder writes built tasks, which Bench runs and scores. Inside a task, the agent calls Perception's encoders through the perception service: Perception's gateway, which Bench starts beside the agent, with a call budget and a call log. Tasks, traces and results stay on your machine. [Architecture](learn/architecture.md) shows the layout.

## Where next

- [Get started](get-started.md): install and score a first run on dummy data.
- [Design principles](learn/principles.md): how MedOmni treats data, tasks and contributions, and where its design comes from.
- [Concepts](learn/concepts.md): the terms used across these docs.
- [Architecture](learn/architecture.md): the repository layout and how the projects fit.
