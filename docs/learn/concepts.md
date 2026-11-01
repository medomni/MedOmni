# Concepts

The ideas behind MedOmni. Each entry links to the page with the details.

## Projects

**Project**
:   A part of MedOmni with its own folder, package, command and docs section. Projects depend on Core and not on each other. v0.3.0 has two: Bench and Perception.

**Core**
:   What every project uses: the contracts, the `medomni` command, plug-in loading, the testing kit and the audit. Only the MedOmni team changes it. See [Architecture](architecture.md).

**Bench**
:   The project that evaluates AI agents on medical tasks. It builds tasks from your data, runs an agent on them in Harbor, with or without encoders, and scores the answers. See [Run your agent](../guides/run-your-agent.md).

**Perception**
:   The project that turns medical data into evidence an agent can use. It serves the encoders through the gateway. See [Use the encoders](../guides/use-the-encoders.md).

## Data and encoders

**Dataset**
:   A source of patient data, used under its own license: MIMIC-IV, AI-READI, BDSP or VitalDB. MedOmni ships no data. See [Datasets](bench/datasets.md).

**Family**
:   A declared input format, such as 12-lead ECG at 500 Hz. Datasets supply families; encoders read them. See [Families](core/families.md).

**Encoder**
:   A containerised model or rule that reads one family and returns evidence: labels, events, text or embeddings, with their provenance and reliability. See [Encoders](perception/encoders.md).

**Gateway**
:   The HTTP service in Perception that lists encoders, serves their model cards and runs them. Agents and your own code call encoders through it. See [Gateway](perception/gateway.md).

## Evaluation

**Task**
:   A clinical question asked of each patient in a cohort, with one fixed way to score the answers. A task spec defines it; Bench builds one atom task per patient. See [Tasks](bench/tasks.md).

**Agent**
:   The system being evaluated: a scaffold driving a model, described in an agent config. See [Runs](bench/runs.md).

## Extending MedOmni

**Contract**
:   A versioned format with the validator that checks it, such as the task spec or the model card. Projects and plug-in packages depend only on contracts. See [Contracts](core/contracts.md).

**Extension point**
:   A place where contributors add to MedOmni: agent, dataset adapter or task in Bench, encoder in Perception. Each has a template and one check command, and is filled by pull request or from a plug-in package. See [Contribute](../guides/contribute.md).
