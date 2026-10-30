# MedOmni

MedOmni is a benchmark that runs AI agents on medical tasks across many data modalities and scores what they do.

Each task gives an agent one patient's evidence (tables, waveforms, images, notes) and asks a clinical question. The agent can call perception encoders as tools, and a fixed verifier scores its answer. Like Terminal-Bench and SWE-bench, MedOmni measures agent behaviour, not a single model.

!!! info "This is v0.2.1"
    These docs describe MedOmni v0.2.1 (git tag `v0.2.1`). Its code is that of v0.2.0, the first version that works end to end, from raw clinical data to scored agent runs. It runs from a checkout of the repository; there is no installable package yet.

!!! warning "No patient data ships with MedOmni"
    The repository holds code and task specs. Tasks are built locally from MIMIC-IV, AI-READI and BDSP, which you must be licensed to use.

## Who it is for

| You are | You want to | Start here |
|---|---|---|
| **Agent evaluator** | Run an agent on MedOmni tasks and read the scores | [Run your agent](guides/run-your-agent.md) |
| **Encoder user** | Call the MedOmni encoders over HTTP | [Use the encoders](guides/use-the-encoders.md) |
| **Contributor** | Add a task, an agent config or an encoder | [Contribute](guides/contribute.md) |

## How it fits together

MedOmni builds tasks from your licensed data, runs agents on them under [Harbor](https://github.com/laude-institute/harbor) and scores the runs; traces and results stay on your machine. [Architecture](learn/architecture.md) shows the parts.

## Where next

- [Get started](get-started.md): set up a checkout and run a first experiment.
- [Design principles](learn/principles.md): how MedOmni treats data and tasks, and how these docs are written.
- [Concepts](learn/concepts.md): the terms used across these docs.
- [Architecture](learn/architecture.md): how the parts fit.
