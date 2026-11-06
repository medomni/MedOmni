# Concepts

The ideas behind MedOmni. Each entry links to the page with the details.

## Projects

**Project**
:   A part of MedOmni with its own package, content folder, command and docs section. v0.3.0 has three: Bench, Perception and Studio. Bench and Perception depend on Core and not on each other; Studio may also use them.

**Core**
:   What every project uses: the contracts, the `medomni` command, plug-in loading, dataset loading, recipes, families, the cache and the testing kit. Projects register with it; it imports none of them. Only the MedOmni team changes it. See [Architecture](architecture.md).

**Bench**
:   The project that evaluates AI agents on medical tasks. It builds tasks from your data, runs an agent on them in Harbor, with or without encoders, and scores the answers. See [Run your agent](../guides/run-your-agent.md).

**Studio**
:   The project for the work people do around Bench and Perception: dataset survey, task proposals, review and sign-off, cohort previews, the audit and reports. A proposal ends in a frozen task template. See [Studio](studio/overview.md).

**Perception**
:   The project that turns medical data into evidence an agent can use. It serves the encoders through the gateway. See [Use the encoders](../guides/use-the-encoders.md).

## Data and encoders

**Dataset**
:   A source of patient data, used under its own license: MIMIC-IV, AI-READI, BDSP or VitalDB. MedOmni ships no data. A dataset package, which is configuration only, says how to read it. See [Datasets](bench/datasets.md).

**Event table**
:   The table every dataset becomes: one row per event, with raw files as `FILE//<family>` rows. Every later step reads it. See [Datasets](bench/datasets.md#event-table).

**Family**
:   A declared input format, such as 12-lead ECG at 500 Hz. Datasets supply files in families; encoders read them. See [Families](core/families.md).

**Encoder**
:   A containerised model or rule that reads one family and returns evidence: labels, events, text or embeddings, with their provenance and reliability. See [Encoders](perception/encoders.md).

**Gateway**
:   The HTTP service in Perception that lists encoders, serves their model cards and runs them. Agents and your own code call encoders through it. See [Gateway](perception/gateway.md).

## Evaluation

**Task template**
:   A clinical question with its targets, input and evidence variants, and an `agent` block with the agent's instruction and environment. A frozen template is the end of Make. See [Tasks](bench/tasks.md).

**Cohort**
:   A recipe next to a template: who is included, at which prediction time, and how many per class. A template and a cohort are written `<template>@<cohort>`. See [Recipes](bench/recipes.md).

**Recipe**
:   The one format for what Build takes from a dataset: the cohort, the labels and the evidence. It holds rules, never patient ids. See [Recipes](bench/recipes.md).

**Build**
:   The step in Bench that turns a template, a cohort and your copy into atom tasks with a fixed fingerprint. See [Build](bench/build.md).

**Atom task**
:   One patient's evidence and the question, at the patient's prediction time: the unit an agent runs. See [Tasks](bench/tasks.md#atom-task).

**Task set**
:   A published list of `<template>@<cohort>` pairs pinned to fingerprints, such as `v1`. Scores are compared on task sets. See [Tasks](bench/tasks.md#task-set).

**Cache**
:   The results of slow steps, built the same way by every user and checked against published hashes. See [Cache](core/cache.md).

**Intelligence**
:   The system being evaluated, with a kind. v0.3.0 has one kind, `agent`: a scaffold driving a model, described in an agent config. Records name it as `intelligence: {kind, name}`. See [Runs](bench/runs.md).

## Extending MedOmni

**Contract**
:   A versioned format with the validator that checks it, such as the task template or the model card. Projects and plug-in packages depend only on contracts. See [Contracts](core/contracts.md).

**Extension point**
:   A place where contributors add to MedOmni: agent, dataset or task in Bench, encoder in Perception. Each has a `new` command that writes its starting files and one check command, and is filled by pull request or from a plug-in package. See [Contribute](../guides/contribute.md).
