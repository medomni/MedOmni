# Architecture

MedOmni v0.3.0 in five views:

- the repository layout
- who uses it ([C4](https://c4model.com) C1)
- its containers (C2)
- the components inside the `medomni` package (C3)
- C1 to C3 nested in one picture

## Repository layout

The repository holds one package, `medomni`: Core and two projects. Each folder below maps to a component in the C3 view.

```text
MedOmni/
├── core/                 medomni.core
│   ├── cli/              the medomni command
│   ├── contracts/
│   │   ├── schemas/      task spec, model card, Gateway API, dataset policy, results row
│   │   └── families/     family registry and aliases
│   ├── plugins/          entry-point loading
│   ├── testing/          the checks behind every check command
│   └── audit/            the audit matrix
├── bench/                medomni.bench
│   ├── datasets/         <dataset>/: adapter and policy; the dummy-data generator
│   ├── tasks/
│   │   ├── builder/      spec to atom tasks, fingerprints
│   │   ├── specs/        one spec per task
│   │   └── batches/      pinned task lists
│   ├── harness/          Harbor jobs, route check, run records
│   ├── scoring/          scorer and metrics
│   ├── agents/           contributed agent configs
│   ├── templates/        agent, dataset
│   └── tests/
├── perception/           medomni.perception
│   ├── registry/         catalogue, image pulls, encoder check
│   ├── gateway/          the HTTP service and its sidecar rules
│   ├── runtime/          serving code inside every encoder image
│   ├── encoders/         <family>/<encoder>/: built into images, not installed
│   ├── templates/        encoder
│   └── tests/
├── docs/                 this site
└── pyproject.toml
```

- **One name per project.** Its folder, package, command and docs section use the same name: `perception/`, `medomni.perception`, `medomni perception …`, Perception.
- **Projects depend only on Core.** Each project folder holds its own code, templates and tests. [Design principles](principles.md#structure) gives the rules.
- **One page per component.** Core: [Contracts](core/contracts.md), [Families](core/families.md), [Plug-ins](core/plugins.md), [Audit](core/audit.md). Bench: [Datasets](bench/datasets.md), [Tasks](bench/tasks.md), [Runs](bench/runs.md), [Scoring](bench/scoring.md). Perception: [Encoders](perception/encoders.md), [Gateway](perception/gateway.md).

## Context (C1)

![C1: MedOmni v0.3.0 in context](../assets/c1-context.drawio.svg)

- **Agent evaluator**: describes an agent, runs it on a batch with Bench, reads the scores.
- **Encoder user**: calls the encoders through Perception's gateway.
- **Contributor**: adds an agent, a dataset adapter, a task or an encoder through its extension point.
- **MedOmni**: one package with one command, holding Core, Bench and Perception.
- **Plug-in packages**: outside `medomni-*` packages that add agents, dataset adapters, tasks or encoders without a pull request.
- **Datasets**: MIMIC-IV, AI-READI and BDSP under your own license, and VitalDB, read from local disk.
- **Harbor**: the agent-evaluation framework that runs each atom task in Docker.
- **Model provider**: the API behind an agent's model on a `cloud` route. A `local` route needs none.
- **Container registry**: the published gateway and encoder images (`ghcr.io/medomni`).
- **Hugging Face**: model cards and the public task samples of open datasets.

## Containers (C2)

![C2: the containers, grouped by project](../assets/c2-containers.drawio.svg)

| Container | Project | Does |
|---|---|---|
| `medomni` command | Core | The entrance: loads the contracts and any plug-in packages, then hands each subcommand to its project. Also runs the audit. |
| Workspace | Core | Configuration, built tasks, runs and the results file, on your machine. Never committed. |
| Bench library | Bench | Builds tasks from your data, turns a batch into Harbor jobs, records runs and scores them. |
| Perception library | Perception | Pulls encoder images, starts the gateway and checks encoders. |
| Gateway | Perception | The HTTP service that lists encoders, serves model cards and runs encoders. Also runs inside each atom task as the perception sidecar. |
| Encoders | Perception | One image per encoder, each reading one family. Published to the container registry; model cards to Hugging Face. |

Gateway and encoder images are tagged with the MedOmni version that built them, so every image names the contract version it implements.

## Components of the package (C3)

![C3: the components inside the medomni package](../assets/c3-components.drawio.svg)

| Project | Component | Module | Does |
|---|---|---|---|
| Core | Command | `medomni.core.cli` | The `medomni` command: every subcommand in [Commands](../cli/index.md). |
| Core | Contracts | `medomni.core.contracts` | The versioned formats and their validators: family registry, task spec, model card, Gateway API, dataset policy, results row, fingerprint. |
| Core | Plug-ins | `medomni.core.plugins` | Finds installed plug-in packages through their entry points. |
| Core | Testing kit | `medomni.core.testing` | The checks behind every check command, importable by plug-in packages. |
| Core | Audit | `medomni.core.audit` | The [audit](../reference/audit.md) of data, families, encoders, tasks and runs. |
| Bench | Datasets | `medomni.bench.datasets` | One adapter and one policy per dataset, and the dummy-data generator. |
| Bench | Tasks | `medomni.bench.tasks` | Task specs, the task builder, batches, and the check against published fingerprints. |
| Bench | Harness | `medomni.bench.harness` | Turns a batch into Harbor jobs, checks the route against each dataset policy and records runs. |
| Bench | Scorer | `medomni.bench.scoring` | Scores complete tasks. The only thing that writes scores. |
| Perception | Registry | `medomni.perception.registry` | The encoder catalogue: model cards, images, pulls and the encoder check. |
| Perception | Gateway | `medomni.perception.gateway` | The gateway service, built into the gateway image. |

The four extension points plug into the projects, by pull request or from a plug-in package:

| Extension point | Project | Template | Check | Entry-point group |
|---|---|---|---|---|
| Agent | Bench | `bench/templates/agent/` | `medomni bench run` on `smoke-dummy` | `medomni.agents` |
| Dataset adapter | Bench | `bench/templates/dataset/` | `medomni bench data check` | `medomni.datasets` |
| Task | Bench | `medomni bench task new` | `medomni bench task check` | `medomni.tasks` |
| Encoder | Perception | `perception/templates/encoder/` | `medomni perception check` | `medomni.encoders` |

## All levels

![C1 to C3 nested: the system, its containers, and the package components](../assets/c1-c3-overview.drawio.svg)

## Where next

- [Design principles](principles.md): the principles behind this layout.
- [Reference](../reference/tasks.md): the contracts each project reads and writes.
- [Commands](../cli/index.md): every subcommand.
