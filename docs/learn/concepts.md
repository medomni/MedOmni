# Concepts

The terms used across MedOmni, in the order a run meets them.

**Dataset**
:   A source of patient data you obtain under its own license: MIMIC-IV, AI-READI or BDSP in v0.2.1. MedOmni ships none.

**Task**
:   A clinical question asked of each patient in a cohort, with a fixed way to score the answers. Each task type is defined by a task spec, a yaml file in `data_task/taskbuilder/specs/`.

**Atom task**
:   One task for one patient: the unit an agent runs. A task type's atom tasks are scored together, against answers the agent never sees.

**Fingerprint**
:   A hash of a task's content. The same spec on the same data gives the same fingerprint, so anyone with the data can rebuild a task and prove it matches.

**Batch**
:   A named, pinned list of tasks and their fingerprints.

**Family**
:   Inputs that can share an encoder are one family, defined by a declared format such as 12-lead ECG at 500 Hz. Datasets supply families; encoders read them.

**Encoder**
:   A containerised model or rule that reads one family and returns evidence an agent can use, such as labels, events or text.

**Model card**
:   An encoder's declared facts: what it reads and returns, where it comes from, its license and its known limits.

**Gateway**
:   The HTTP service through which an agent finds encoders, reads their model cards and calls them.

**Agent**
:   The system being evaluated: a scaffold (`terminus-2` in v0.2.1) driving a model.

**Condition**
:   What encoder access an agent gets: with encoders (`enc`), without (`noenc`), or required to use at least one (`enc-forced`). Only the encoder access, and the instruction paragraph that describes it, differ. The config calls it `variant`.

**Experiment**
:   One yaml file declaring which agents run which task types, under which conditions, how many times.

**Run**
:   One agent on one atom task, once. Its outcome is recorded in the results file, and scoring turns the runs of one task type into a score.
