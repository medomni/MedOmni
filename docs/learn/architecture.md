# Architecture

MedOmni v0.3.0 in five views:

- the repository layout
- who uses it ([C4](https://c4model.com) C1)
- its containers (C2)
- the components inside the `medomni` package (C3)
- C1 to C3 nested in one picture

## Repository layout

The repository holds one package, `medomni`: Core and two projects. Code is under `src/`; content that people write and review (families, specs, task suites, agent configs, encoders, templates) is in one top-level folder per project.

```text
MedOmni/
├── src/medomni/
│   ├── core/                 medomni.core
│   │   ├── cli/              the medomni command
│   │   ├── contracts/        typed models, validators, schemas/
│   │   ├── plugins/          entry-point loading
│   │   ├── testing/          runs the checks each project registers
│   │   └── audit/            runs the audit checks each project registers
│   ├── bench/                medomni.bench
│   │   ├── datasets/         <dataset>/: adapter and policy; the dummy-data generator
│   │   ├── tasks/            the task pipeline, task suites, fingerprints
│   │   ├── harness/          Harbor jobs, route check, run records
│   │   ├── service/          the perception service in each atom task
│   │   └── scoring/          scorer, metrics, behaviour metrics
│   └── perception/           medomni.perception
│       ├── registry/         catalogue, image pulls, encoder check
│       ├── runtime/          serving code built into every encoder image
│       └── gateway/          the HTTP service
├── core/
│   └── families/             one file per family, and aliases.yaml
├── bench/
│   ├── specs/                one spec per task
│   ├── suites/               task suites: pinned task lists
│   ├── agents/               contributed agent configs
│   └── templates/            agent, dataset
├── perception/
│   ├── encoders/             <family>/<encoder>/: built into images, not installed
│   └── templates/            encoder
├── tests/                    core/, bench/, perception/
├── docs/                     this site
└── pyproject.toml
```

- **One name per project.** Its package, content folder, command and docs section use the same name: `medomni.perception`, `perception/`, `medomni perception …`, Perception.
- **Code and content are apart.** A new task, family or encoder changes content only; the code that reads it is unchanged.
- **Projects depend only on Core.** Bench and Perception never import each other. They register their commands, checks and audit checks with Core; see [How Core finds the projects](#how-core-finds-the-projects). [Design principles](principles.md#structure) gives the rules.
- **One page per component.** Core: [Contracts](core/contracts.md), [Families](core/families.md), [Plug-ins](core/plugins.md), [Audit](core/audit.md). Bench: [Datasets](bench/datasets.md), [Tasks](bench/tasks.md), [Runs](bench/runs.md), [Scoring](bench/scoring.md). Perception: [Encoders](perception/encoders.md), [Gateway](perception/gateway.md).

## Context (C1)

![C1: MedOmni v0.3.0 in context](../assets/c1-context.drawio.svg)

- **Agent evaluator**: describes an agent, runs it on a task suite with Bench, reads the scores.
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
| `medomni` command | Core | The entrance: finds the projects and any plug-in packages through entry points, then hands each subcommand to its project. |
| Workspace | Core | Configuration, caches, built tasks, runs and the results file, on your machine. Never committed. |
| Bench library | Bench | Builds tasks from your data, turns a task suite into Harbor jobs, records runs and scores them. |
| Perception service | Bench | Runs inside each atom task with encoders: Perception's gateway, with Bench's call budget, family filter and call log. |
| Perception library | Perception | Pulls encoder images, starts the gateway and checks encoders. |
| Gateway | Perception | The HTTP service that lists encoders, serves model cards and runs encoders. |
| Encoders | Perception | One image per encoder, each reading one family. Published to the container registry; model cards to Hugging Face. |

Gateway and encoder images are tagged with the MedOmni release that built them. The gateway runs any encoder image built since the Container API last changed.

## Components of the package (C3)

![C3: the components inside the medomni package](../assets/c3-components.drawio.svg)

| Project | Component | Module | Does |
|---|---|---|---|
| Core | Command | `medomni.core.cli` | The `medomni` command. Finds each project's subcommands through entry points; see [Commands](../cli/index.md). |
| Core | Contracts | `medomni.core.contracts` | The versioned formats, each with a typed model and a validator. See [Contracts](core/contracts.md). |
| Core | Plug-ins | `medomni.core.plugins` | Loads the projects and plug-in packages through their entry points. |
| Core | Testing kit | `medomni.core.testing` | Runs the checks each project registers. Plug-in packages import it for their own CI. |
| Core | Audit | `medomni.core.audit` | Runs the audit checks each project registers and writes the [audit](../reference/audit.md) report. |
| Bench | Datasets | `medomni.bench.datasets` | One adapter and one policy per dataset, and the dummy-data generator. |
| Bench | Tasks | `medomni.bench.tasks` | The task pipeline, task suites and fingerprints. |
| Bench | Harness | `medomni.bench.harness` | Turns a task suite into Harbor jobs, checks the route against each dataset policy and records runs. |
| Bench | Scorer | `medomni.bench.scoring` | Scores complete tasks, one score record per target. The only thing that writes scores. |
| Bench | Perception service | `medomni.bench.service` | Runs the gateway inside each atom task, with the call budget, family filter and call log. |
| Perception | Gateway | `medomni.perception.gateway` | The gateway service, built into the gateway image. |
| Perception | Registry | `medomni.perception.registry` | The encoder catalogue: model cards, images, pulls and the encoder check. |

The projects meet in one contract: the perception service calls Perception's gateway through the Gateway API. Bench imports no Perception code.

Contributors and plug-in packages add agents, datasets, tasks and encoders to the projects; [Extend MedOmni](extend.md) lists each extension point with its template and check.

## How Core finds the projects

Core is the `medomni` command and the shared machinery. It imports no project; each project tells Core what it adds, through the `medomni.projects` entry-point group in MedOmni's own `pyproject.toml`:

- its subcommands, such as `medomni bench …`
- the checks behind its check commands
- its audit checks

This is internal wiring, done once per project. Users never do it; a later project joins the same way. Outside packages that add pieces use [plug-ins](core/plugins.md) instead.

## All levels

![C1 to C3 nested: the system, its containers, and the package components](../assets/c1-c3-overview.drawio.svg)

## Where next

- [Design principles](principles.md): the principles behind this layout.
- [Reference](../reference/tasks.md): the contracts each project reads and writes.
- [Commands](../cli/index.md): every subcommand.
