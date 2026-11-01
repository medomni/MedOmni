# Python API

The `medomni` package has one subpackage per project. The command calls these modules; use them directly to script MedOmni from Python.

| Module | Holds |
|---|---|
| `medomni.core.contracts` | The versioned contracts and their validators: family registry, task spec, model card, Gateway API, dataset policy, results row, fingerprint. |
| `medomni.core.plugins` | Discovery of plug-in packages through the entry-point groups `medomni.agents`, `medomni.datasets`, `medomni.tasks` and `medomni.encoders`. |
| `medomni.core.testing` | The checks behind every check command, for use in a plug-in package's own tests. |
| `medomni.core.audit` | The audit. |
| `medomni.core.cli` | The `medomni` command. |
| `medomni.bench.datasets` | One adapter and one policy per dataset, and the dummy-data generator. |
| `medomni.bench.tasks` | Task specs, the task builder, batches, and the check against published fingerprints. |
| `medomni.bench.harness` | Harbor jobs, the route check and run records. |
| `medomni.bench.scoring` | The scorer. |
| `medomni.perception.registry` | The encoder catalogue: model cards, image pulls and the encoder check. |
| `medomni.perception.gateway` | The gateway service. |

Every module depends on `medomni.core.contracts`. `medomni.bench` and `medomni.perception` never import each other.

## Where next

- [Commands](../cli/index.md): the same functions as commands.
- [Architecture](../learn/architecture.md): how the modules fit.
