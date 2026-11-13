# Architecture

MedOmni v0.3.0 in five views:

- the repository layout
- who uses it ([C4](https://c4model.com) C1)
- its containers (C2)
- the components inside the `medomni` package (C3)
- C1 to C3 nested in one picture

## Repository layout

The repository holds one package, `medomni`: Core and three projects. Code is under `src/`; content that people write and review (families, dataset packages, task templates, cohorts, benchmarks, agent configs, encoders) is in one top-level folder per project. The starting files that each `new` command writes are inside the package.

```text
MedOmni/
├── src/medomni/
│   ├── core/                 medomni.core
│   │   ├── cli/              the medomni command
│   │   ├── contracts/        typed models, validators, schemas/
│   │   ├── plugins/          entry-point loading
│   │   ├── loading/          format readers (CSV, OMOP, folder trees, recording headers) and the loader
│   │   ├── families/         registry loader, converter interface, dummy-data generator
│   │   ├── cache/            cache backends, cache commands
│   │   ├── tasks/            built tasks: atom layout, task sets, checks, the atom's shared Harbor parts
│   │   ├── builders.py       TaskBuilder, the interface every task builder follows
│   │   └── testing/          runs the checks each project registers
│   ├── bench/                medomni.bench
│   │   ├── runs/             runner interface, Harbor runner (assets/harbor/), replay; run and prediction records
│   │   ├── arms/             the run side of the four built-in arms
│   │   ├── scoring/          scorer, behaviour metrics
│   │   └── metrics.py        auc, qwk, mae
│   ├── perception/           medomni.perception
│   │   ├── registry/         catalogue, image builds and pulls
│   │   ├── runtime/          serving code built into every encoder image
│   │   ├── gateway/          the HTTP service
│   │   └── sidecar/          the perception service: the gateway beside each atom task's agent
│   └── studio/               medomni.studio
│       ├── build/            the medomni-v1 builder: its recipe format, task steps, cohort selection, its checks, the arms' build side, config hashes
│       └── survey/, propose/, review/ (with the audit), preview/, assets/, report/
├── core/
│   └── families/             one file per family, and aliases.yaml
├── bench/
│   ├── benchmarks/<benchmark>/  benchmark.yaml (the card), sets/ (task sets: pinned <template>@<cohort> lists)
│   └── agents/               contributed agent configs
├── perception/
│   └── encoders/             <family>/<encoder>/: built into images, not installed
├── studio/
│   ├── datasets/<dataset>/   dataset package: dataset.yaml, labels.yaml, evidence.yaml,
│   │                         codes.csv, policy.yaml, hooks/, tasks/<template>/
├── tests/                    core/, bench/, perception/, studio/
├── docs/                     this site
└── pyproject.toml
```

- **One name per project.** Its package, content folder, command and docs section use the same name: `medomni.perception`, `perception/`, `medomni perception …`, Perception.
- **Code and content are apart.** A new dataset, task, family or encoder changes content only; the code that reads it is unchanged.
- **Projects depend only on Core.** Bench and Perception never import each other. Studio may also import Bench and Perception; nothing imports Studio. They register their commands, checks, content kinds and audit checks with Core; see [How Core finds the projects](#how-core-finds-the-projects). [Design principles](principles.md#structure) gives the rules.
- **Studio builds, Bench runs and scores.** They meet at the [built-task](core/built-tasks.md) contract, so Bench runs a task whoever built it, and runs and scores with Studio removed.
- **Core names no content.** No dataset, benchmark, arm, runner or project folder is named in Core's code; MedOmni's own are the first of each kind, registered like any other.
- **One page per component.** Core: [Contracts](core/contracts.md), [Built tasks](core/built-tasks.md), [Families](core/families.md), [Cache](core/cache.md), [Plug-ins](core/plugins.md). Bench: [Runs](bench/runs.md), [Scoring](bench/scoring.md). Studio: [Overview](studio/overview.md), [Datasets](studio/datasets.md), [Tasks](studio/tasks.md), [Build](studio/build.md), [Recipes](studio/recipes.md), [Audit](studio/audit.md). Perception: [Encoders](perception/encoders.md), [Gateway](perception/gateway.md).

## Context (C1)

![C1: MedOmni v0.3.0 in context](../assets/c1-context.drawio.svg)

- **Agent evaluator**: describes an agent, builds a task set from their own data with Studio, runs the agent on it with Bench, reads the scores.
- **Encoder user**: calls the encoders through Perception's gateway.
- **Contributor**: adds an agent, a dataset, a task or an encoder through its extension point, and proposes and reviews tasks in Studio.
- **MedOmni**: one package with one command, holding Core, Bench, Perception and Studio.
- **Plug-in packages**: outside `medomni-*` packages that add agents, datasets, tasks or encoders without a pull request.
- **Datasets**: MIMIC-IV, AI-READI and BDSP under your own license, and VitalDB, read from local disk.
- **Harbor**: the agent-evaluation framework that runs each atom task in Docker.
- **Model provider**: the API behind an agent's model on a `cloud` route. A `local` route needs none.
- **Container registry**: where `medomni perception pull` pulls encoder images from (`ghcr.io/medomni`). Nothing is published there yet; images are built on your machine.
- **Hugging Face**: model cards, and dummy data for each dataset. No real record is published there.

## Containers (C2)

![C2: the containers, grouped by project](../assets/c2-containers.drawio.svg)

| Container | Project | Does |
|---|---|---|
| `medomni` command | Core | The entrance: finds the projects through entry points and the plug-in packages' content folders and entry points, then hands each subcommand to its project. |
| Workspace | Core | Configuration, the cache, built atom tasks, the run folders and the results file, on your machine. Never committed. |
| Bench library | Bench | Checks built tasks, turns a task set into Harbor jobs, records runs and scores them. |
| Perception service | Bench | Runs inside each atom task with encoders: Perception's gateway, with Bench's call budget, family filter and call log. |
| Perception library | Perception | Builds and checks encoder images, and starts the gateway. |
| Gateway | Perception | The HTTP service in front of every encoder: its catalogue finds encoders and serves model cards, its router sends each call to a running encoder container. |
| Encoders | Perception | One image per encoder, each reading one family. Built on your machine; model cards on Hugging Face. |
| Studio tools | Studio | Build atom tasks from your data with the `medomni-v1` builder, survey datasets, collect and review task proposals, preview cohorts, run the audit and report results. |

Gateway and encoder images are tagged with the MedOmni release that built them. The gateway runs any encoder image built since the Container API last changed.

## Components of the package (C3)

![C3: the components inside the medomni package](../assets/c3-components.drawio.svg)

| Project | Component | Module | Does |
|---|---|---|---|
| Core | Command | `medomni.core.cli` | The `medomni` command. Finds each project's subcommands through entry points; see [Commands](../cli/index.md). |
| Core | Contracts | `medomni.core.contracts` | The versioned formats, each with a typed model and a validator. See [Contracts](core/contracts.md). |
| Core | Plug-ins | `medomni.core.plugins` | Finds the projects' entry points, and the plug-in packages' content folders and entry points. |
| Core | Testing kit | `medomni.core.testing` | Runs the checks each project registers. Plug-in packages import it for their own CI. |
| Core | Loading | `medomni.core.loading` | The format readers, and the loader that runs a dataset package through them into its event table. |
| Core | Families | `medomni.core.families` | The family registry, the converter interface and the dummy-data generator. |
| Core | Cache | `medomni.core.cache` | The cache backend call, the `folder` and `none` backends, and the cache commands. See [Cache](core/cache.md). |
| Core | Built tasks | `medomni.core.tasks`, `medomni.core.builders` | The atom layout, task sets, the checks on built tasks, and the `TaskBuilder` interface. See [Built tasks](core/built-tasks.md). |
| Bench | Harness | `medomni.bench.runs` | The agent runner: turns a task set into Harbor jobs and records runs and prediction records. |
| Bench | Arms | `medomni.bench.arms` | The run side of the four built-in arms. The harness looks up any arm by its registered name. |
| Bench | Scorer | `medomni.bench.scoring` | Scores complete tasks from their prediction records, one score record per target. The only thing that writes scores. |
| Perception | Gateway | `medomni.perception.gateway` | The gateway service, built into the gateway image. |
| Perception | Registry | `medomni.perception.registry` | The encoder catalogue: model cards, images, pulls and the encoder check. |
| Perception | Perception service | `medomni.perception.sidecar` | The gateway beside each atom task's agent, with the call budget, family filter and call log. Bench starts it through `medomni.services`. |
| Studio | Build | `medomni.studio.build` | The `medomni-v1` builder: its recipe format (task templates, cohorts, labels, evidence) and the engine that runs recipes into atom tasks, with the arms' build side and config hashes. See [Build](studio/build.md). |
| Studio | Tools | `medomni.studio` | One subpackage per tool kind: survey, propose, review (with the audit), preview, assets, report. |

The projects meet in contracts: Studio's builder writes built tasks that Bench reads, and Bench starts Perception's perception service through the `medomni.services` entry point and talks to it only through the Gateway API. Bench imports no Perception code and no Studio code.

Contributors and plug-in packages add agents, datasets, tasks and encoders to the projects; [Extend MedOmni](extend.md) lists each extension point with its template and check.

## How Core finds the projects

Core is the `medomni` command and the shared machinery. It imports no project; each project tells Core what it adds, through entry points in MedOmni's own `pyproject.toml`:

- its subcommands, such as `medomni bench …`, in `medomni.commands`
- the checks behind its check commands, and its audit checks, in `medomni.checks`
- its content kinds, each a folder pattern and its contract, such as `studio/datasets/*/dataset.yaml`, in `medomni.content`
- a service a run starts beside the agent, such as Perception's perception service, in `medomni.services`

This is internal wiring, done once per project. Users never do it; a later project joins the same way. Outside packages that add pieces use [plug-ins](core/plugins.md) instead.

## All levels

![C1 to C3 nested: the system, its containers, and the package components](../assets/c1-c3-overview.drawio.svg)

## Where next

- [Design principles](principles.md): the principles behind this layout.
- [Reference](../reference/tasks.md): the contracts each project reads and writes.
- [Commands](../cli/index.md): every subcommand.
