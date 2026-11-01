# Python API

The `medomni` package has one subpackage per project. The command calls these modules; use them directly to script MedOmni from Python.

| Module | Holds |
|---|---|
| `medomni.core.contracts` | The versioned contracts: a typed model and a validator for each. See [Contracts](../learn/core/contracts.md). |
| `medomni.core.plugins` | Loading of projects and plug-in packages through entry points. |
| `medomni.core.testing` | The check runner, for use in a plug-in package's own tests. |
| `medomni.core.audit` | The audit runner and report. |
| `medomni.core.cli` | The `medomni` command. |
| `medomni.bench.datasets` | One adapter and one policy per dataset, the family bridge and the dummy-data generator. |
| `medomni.bench.tasks` | The task pipeline, batches and fingerprints. |
| `medomni.bench.harness` | Harbor jobs, the route check, run records and the replay agent. |
| `medomni.bench.sidecar` | The sidecar inside each atom task. |
| `medomni.bench.scoring` | The scorer, the metrics and the behaviour metrics. |
| `medomni.perception.registry` | The encoder catalogue: model cards, image pulls and the encoder check. |
| `medomni.perception.runtime` | The encoder interface and the serving code built into every image. |
| `medomni.perception.gateway` | The gateway service. |

- `medomni.core` imports no project.
- `medomni.bench` and `medomni.perception` import only `medomni.core`, never each other.
- Projects register their commands, checks and audit checks with Core through entry points; see [Plug-ins](../learn/core/plugins.md).

## Where next

- [Commands](../cli/index.md): the same functions as commands.
- [Architecture](../learn/architecture.md): how the modules fit.
