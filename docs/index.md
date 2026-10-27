# MedOmni

MedOmni is a benchmark that runs AI agents on medical tasks across many data modalities and scores what they do.

Each task gives an agent one patient's evidence (tables, waveforms, images, notes) and asks a clinical question. The agent can call perception encoders as tools, and a fixed verifier scores its answer. Like Terminal-Bench and SWE-bench, MedOmni measures agent behaviour, not a single model.

!!! info "Scope"
    No patient data ships with MedOmni. The package carries code, contracts and task specs. Data comes from generated dummy data, from open datasets such as VitalDB, or from datasets you are licensed to use, such as MIMIC-IV.

## Who it is for

| You are | You want to | Start here |
|---|---|---|
| **Model tester or practitioner** | Run your agent on MedOmni tasks and read the scores | [Run your agent](guides/run-your-agent.md) |
| **Perception service user** | Call the MedOmni encoders as tools in your own system | [Use the encoders](guides/use-the-encoders.md) |
| **Task adder** | Add tasks on open data, a dataset adapter or an encoder | [Contribute](guides/contribute.md) |

## How it fits together

![MedOmni system context](assets/c1-context.drawio.svg)

You install one package, `pip install medomni`, and use one command, `medomni`. Encoders run as container images pulled from the GitHub container registry. Task samples and encoder model cards live on Hugging Face. The agent's language model runs locally by default; a cloud model is opt-in and checked against each dataset's policy.

## Where next

- [Get started](get-started.md): install and run a first task on dummy data.
- [Concepts](learn/concepts.md): the terms used across these docs.
- [Architecture](learn/architecture.md): how the parts fit, in three views.
