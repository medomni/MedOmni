# Python API

The `medomni` package has one subpackage per project. The command calls these modules; use them directly to script MedOmni from Python.

| Module | Holds |
|---|---|
| `medomni.core.contracts` | The versioned contracts: a typed model and a validator for each. See [Contracts](../learn/core/contracts.md). |
| `medomni.core.plugins` | Finds the projects' entry points, and the plug-in packages' content folders and entry points. |
| `medomni.core.testing` | The check runner, for use in a plug-in package's own tests. |
| `medomni.core.cli` | The `medomni` command. |
| `medomni.core.loading` | The format readers, and the loader that runs a dataset package through them into its event table. |
| `medomni.core.recipes` | The recipe format: cohorts, labels, evidence. |
| `medomni.core.families` | The family registry, the family converters and the dummy-data generator (`medomni.core.families.dummy`). |
| `medomni.core.cache` | Cache keys, entries and the cache commands. |
| `medomni.bench.build` | Build: the task steps, cohort selection, the checks, task sets and config hashes. |
| `medomni.bench.runs` | The runner interface, the agent runner on Harbor, the replay agent (which repeats recorded runs with no model calls) and the import of v0.2 runs; run and prediction records. |
| `medomni.bench.arms` | The arm interface and the four built-in arms. |
| `medomni.bench.service` | The perception service inside each atom task: the gateway behind the call budget, family filter and call log. |
| `medomni.bench.scoring` | The scorer and the behaviour metrics. |
| `medomni.bench.metrics` | The metrics `auc`, `qwk` and `mae`. |
| `medomni.perception.registry` | The encoder catalogue: model cards, image builds and pulls. |
| `medomni.perception.runtime` | The encoder interface, one decoder per family, and the serving code built into every image. |
| `medomni.perception.gateway` | The gateway service: catalogue, router and evidence. |
| `medomni.studio` | The tools around Bench and Perception, one subpackage per kind: survey, propose, review (with the audit), preview, assets, report. |

- `medomni.core` imports no project.
- `medomni.bench` and `medomni.perception` import only `medomni.core`, never each other.
- `medomni.studio` may import `medomni.core`, `medomni.bench` and `medomni.perception`. Nothing imports it.
- Projects register their commands, checks and audit checks with Core; see [How Core finds the projects](../learn/architecture.md#how-core-finds-the-projects).

## Where next

- [Commands](../cli/index.md): the same functions as commands.
- [Architecture](../learn/architecture.md): how the modules fit.
