# Concepts

The ideas behind MedOmni. Each entry links to the page with the details.

## Projects

**Project**
:   A part of MedOmni with its own package, content folder, command and docs section. v0.3.0 has three: Bench, Perception and Studio. Bench and Perception depend on Core and not on each other; Studio may also use them.

**Core**
:   What every project uses: the contracts, the `medomni` command, plug-in loading, dataset loading, families, the cache, the built-task contract and the testing kit. Projects register with it; it imports none of them. Only the MedOmni team changes it. See [Architecture](architecture.md).

**Bench**
:   The project that evaluates AI agents on medical tasks. It runs an agent on built tasks in Harbor, with or without encoders, and scores the answers, whoever built the tasks. See [Run your agent](../guides/run-your-agent.md).

**Studio**
:   The project that makes and builds tasks, and the work people do around Bench and Perception: dataset survey, task proposals, review and sign-off, cohort previews, MedOmni's task builder, the audit and reports. A proposal ends in a frozen task template, which the builder turns into built tasks. See [Studio](studio/overview.md).

**Perception**
:   The project that turns medical data into evidence an agent can use. It serves the encoders through the gateway. See [Use the encoders](../guides/use-the-encoders.md).

## Data and encoders

**Dataset**
:   A source of patient data, used under its own license: MIMIC-IV, AI-READI, BDSP or VitalDB. MedOmni ships no data. A dataset package, which is configuration only, says how to read it. See [Datasets](studio/datasets.md).

**Event table**
:   The table every dataset becomes: one row per event, with raw files as `FILE//<family>` rows. Every later step reads it. See [Datasets](studio/datasets.md#event-table).

**Family**
:   A declared input format, such as 12-lead ECG at 500 Hz. Datasets supply files in families; encoders read them. See [Families](core/families.md).

**Encoder**
:   A containerised model or rule that reads one family and returns evidence: labels, events, text or embeddings, with their provenance and reliability. See [Encoders](perception/encoders.md).

**Gateway**
:   The HTTP service in Perception that lists encoders, serves their model cards and runs them. Agents and your own code call encoders through it. See [Gateway](perception/gateway.md).

## Evaluation

**Task template**
:   A clinical question with its targets, and an `agent` block with the agent's instruction and environment. A frozen template is the end of Make. See [Tasks](studio/tasks.md).

**Cohort**
:   A recipe next to a template: who is included, at which prediction time, and how many per class. A template and a cohort are written `<template>@<cohort>`, and are one task with a version `N.X`. See [Recipes](studio/recipes.md).

**Recipe**
:   The format MedOmni's builder, `medomni-v1`, reads for what it takes from a dataset: the cohort, the labels and the evidence. It holds rules, never patient ids. See [Recipes](studio/recipes.md).

**Build**
:   MedOmni's task builder, `medomni-v1`, in Studio: it turns a template, a cohort and your copy into atom tasks. See [Build](studio/build.md).

**Task builder**
:   Code that writes built tasks: a content folder with the answers, and one atom task per patient under each arm. Any builder that follows the built-task contract can feed Bench. See [Built tasks](core/built-tasks.md).

**Atom task**
:   One patient's evidence and the question, at the patient's prediction time: the unit an agent runs. See [Built tasks](core/built-tasks.md#the-files).

**Task set**
:   A published list of `<template>@<cohort>` pairs, each pinned at its version, and the arms to build them under. It is named `<benchmark>/<set>`, such as `medomni-bench/v1`. Scores are compared on task sets. See [Tasks](studio/tasks.md#task-set).

**Benchmark**
:   Several task sets under one card: version, owner, license and the intelligence kinds it accepts. MedOmni's own is `medomni-bench`; a plug-in package can publish another. See [Tasks](studio/tasks.md#benchmark).

**Cache**
:   The results of slow steps, kept only to save time: a build with no cache gives the same atom tasks. See [Cache](core/cache.md).

**Intelligence**
:   The system being evaluated, with a kind. v0.3.0 has one kind, `agent`: a scaffold driving a model, described in an agent config. Records name it as `intelligence: {kind, name}`. See [Runs](bench/runs.md).

**Arm**
:   One way of giving the same tasks to the intelligence, compared side by side, as in a clinical trial: with encoders, without them, or adding input families rung by rung. A builder implements what the arm hides or shows; Bench implements what the run attaches. See [Runs](bench/runs.md#arms).

## Extending MedOmni

**Contract**
:   A versioned format with the validator that checks it, such as the task template or the model card. Projects and plug-in packages depend only on contracts. See [Contracts](core/contracts.md).

**Extension point**
:   A place where contributors add to MedOmni: an agent in Bench, a dataset or task in Studio, an encoder in Perception. Each has a `new` command that writes its starting files and one check command, and is filled by pull request or from a plug-in package. See [Contribute](../guides/contribute.md).
