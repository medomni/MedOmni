# Design principles

## Data governance

- **License compliance.** Every use of a source dataset follows its data use agreement and license, and leakage of source data is strictly prevented. MedOmni works directly with raw clinical data and the tasks built from it, so this is the foundational concern at every stage of building and running it.
- **Derived artifacts.** Everything generated from source data is handled as patient data: tasks, answers, traces and results. They are built and kept on the machine that holds your dataset access; the repository holds code and task specs only, and nothing commits or uploads the rest.

## Task reproducibility

- **Determinism.** The same spec on the same data builds the same task, byte for byte.
- **Verifiability.** A task's fingerprint lets anyone with the data rebuild it and check that it matches.

## Docs composition

- **Necessary.** Keep a line only if, without it, a reader would lose how to use MedOmni or a correct understanding of it.
- **No overlap.** Each fact lives on one page; other pages link to it.
- **Nothing key missing.** Whatever a user needs to run, read or extend this version is here.
- **Current terms.** Use the words this version uses, and the same word everywhere.
- **Minimal structure.** Add a new page only when an existing page cannot hold the content.
