# Python API

The `medomni` package has one subpackage per project. The command calls these modules; use them directly to script MedOmni from Python.

| Module | Holds |
|---|---|
| `medomni.core.contracts` | The versioned contracts: a typed model and a validator for each. See [Contracts](../learn/core/contracts.md). |
| `medomni.core.plugins` | Finds the projects' entry points, and the plug-in packages' content folders and entry points. |
| `medomni.core.testing` | The check runner, for use in a plug-in package's own tests. |
| `medomni.core.cli` | The `medomni` command. |
| `medomni.core.loading` | The format readers, and the loader that runs a dataset package through them into its event table. |
| `medomni.core.families` | The family registry, the converter interface and the dummy-data generator (`medomni.core.families.dummy`). |
| `medomni.core.tasks` | Built tasks: the atom layout, task sets, the checks on built tasks and the atom's shared Harbor parts. See [Built tasks](../learn/core/built-tasks.md). |
| `medomni.core.builders` | `TaskBuilder`, the interface every task builder follows, and the `medomni.builders` group. |
| `medomni.core.cache` | The cache backend call, the `folder` and `none` backends, and the cache commands. |
| `medomni.bench.runs` | The runner interface, the agent runner on Harbor, and the replay agent (which repeats recorded runs with no model calls); run and prediction records. |
| `medomni.bench.arms` | The run side of the four built-in arms. |
| `medomni.bench.scoring` | The scorer and the behaviour metrics. |
| `medomni.bench.metrics` | The metrics `auc`, `qwk` and `mae`. |
| `medomni.perception.registry` | The encoder catalogue: model cards, image builds and pulls. |
| `medomni.perception.runtime` | The encoder interface, one decoder per family, and the serving code built into every image. |
| `medomni.perception.gateway` | The gateway service: catalogue, router and evidence. |
| `medomni.perception.sidecar` | The perception service: the gateway beside each atom task's agent, with the call budget, family filter and call log. Bench starts it through `medomni.services`. |
| `medomni.studio.build` | The `medomni-v1` builder: its recipe format (`medomni.studio.build.contracts`) and engine, the task steps, cohort selection, its checks, the arms' build side and config hashes. |
| `medomni.studio` | The tools around Bench and Perception, one subpackage per kind: survey, propose, review (with the audit), preview, assets, report. |

- `medomni.core` imports no project.
- `medomni.bench` and `medomni.perception` import only `medomni.core`, never each other.
- `medomni.studio` may import `medomni.core`, `medomni.bench` and `medomni.perception`. Nothing imports it.
- Projects register their commands, checks and audit checks with Core; see [How Core finds the projects](../learn/architecture.md#how-core-finds-the-projects).

## Where next

- [Commands](../cli/index.md): the same functions as commands.
- [Architecture](../learn/architecture.md): how the modules fit.
