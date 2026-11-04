# Design principles

## Data governance

- **Licenses.** Every use of a dataset follows its license and data use agreement. Source data never leaves the machine that holds the access.
- **Derived data.** Tasks, answers, traces and results built from a dataset count as patient data. They stay in the workspace. The repository holds only code, contracts, dataset packages, templates and recipes.
- **Policies.** Each dataset has a policy read from its license. `medomni bench run` refuses a model route the policy does not allow.

## Task reproducibility

- **Determinism.** The same template and cohort on the same data build the same atom tasks, byte for byte.
- **Rules, not lists.** Cohorts are published as recipes, never as lists of patients.
- **Verification.** Anyone with the data can rebuild a task and check it against its fingerprint. The fingerprint covers content only, never build time or local paths.

## Structure

The last column names the projects each principle comes from.

| Principle | In MedOmni | Learned from |
|---|---|---|
| **One command** | Every user task is a `medomni` subcommand, grouped by project: `medomni bench …`, `medomni perception …`. | Terminal-Bench, SWE-bench |
| **Projects in one repository** | Bench, Perception and the toolkit each have their own package under `src/medomni/`. Bench and Perception depend only on Core; the toolkit may also use Bench. A project moves to its own repository, with its history, when it has its own owner, users and release schedule. | HELM and MedHELM, PyHealth; MONAI and OpenMMLab, which merged repositories back |
| **Versioned contracts** | Projects and plug-in packages depend only on contracts. Contracts change only in a minor release, and files from the previous minor release still load. | MONAI bundles, scverse AnnData, `langchain-core`, the Harbor task format |
| **Locked core** | Only the MedOmni team changes Core. Core imports no project; projects register with it through entry points. Contributors add agents, datasets, tasks and encoders, each from a starter, with one check command. | pytest and MkDocs plug-ins, OpenMMLab registries |
| **Plug-in packages** | An outside `medomni-*` package adds agents, datasets, tasks or encoders through Python entry points, without a pull request. Tasks on data that cannot leave an institution join this way. | HELM, Inspect, lm-eval-harness, Harbor registries |
| **Shared checks** | `medomni.core.testing` runs the same checks in MedOmni's CI and in a plug-in package's CI. | `langchain-tests`, `nf-core lint`, MONAI bundle CI |
| **Harbor as the runner** | Bench runs agents on Harbor. | Terminal-Bench |
| **Credit** | The full history is kept. Every model card and task template lists its authors. | MONAI bundles, MTEB, Terminal-Bench |

## Docs composition

- **Plain language.** Use the most direct word and the fewest words that state the fact. Avoid:
    - slogans and paired phrases ("one X, one Y")
    - contrasts set up for effect ("X, not Y")
    - modifiers that add no fact
- **Bullets.** When content is a list of items, steps or facts, write short bullets, one point each. A bullet need not be a full sentence.
- **Necessary.** Keep a line only if a reader needs it to use or understand MedOmni.
- **No overlap.** Each fact lives on one page; other pages link to it.
- **Complete.** Everything a user needs to run, read or extend this version is here.
- **Current terms.** Use this version's terms, and the same term everywhere.
- **Minimal structure.** Add a page only when no existing page can hold the content.
