# Plug-ins

A plug-in package is an outside Python package, named `medomni-<name>`, that adds agents, datasets, tasks, benchmarks, encoders, arms, task builders, Studio tools or family converters without a pull request. Use one when the work should stay in your repository, for example tasks on data that cannot leave your institution. [Extend MedOmni](../extend.md) compares it with the other ways to add things.

## Content folder

Agents, datasets, tasks, benchmarks and encoders are files. A plug-in package ships them in one folder, laid out like MedOmni's repository:

```text
medomni_myname/content/
├── bench/
│   ├── agents/<agent>.yaml
│   └── benchmarks/<benchmark>/
│       ├── benchmark.yaml         the benchmark card
│       └── sets/<set>.yaml        its task sets
├── studio/
│   └── datasets/<dataset>/        dataset package, with hooks/ and tasks/<template>/
└── perception/
    └── encoders/<family>/<encoder>/
```

- The package registers the folder with one entry point, in the `medomni.plugins` group.
- MedOmni reads the repository first, then each plug-in folder, with the same loader. A piece in a plug-in folder works as it would in the repository.
- Each project registers its content kinds with Core in `medomni.content`: a folder pattern, such as `studio/datasets/*/dataset.yaml`, and the contract its files follow. Core names no project folder of its own.
- Finding the folder runs none of the package's code. Python in a dataset's `hooks/` is imported only when a build uses it.
- Moving a piece between a plug-in and the repository is a folder copy.

## Python pieces

Pieces that are Python code register one entry point each, in the group for their kind:

| Group | Registers | Used by |
|---|---|---|
| `medomni.commands` | A top-level command | The `medomni` command |
| `medomni.checks` | Checks for the testing kit | [The testing kit](#the-testing-kit) |
| `medomni.content` | A content kind: a folder pattern and its contract | Core's loader and `medomni contracts check` |
| `medomni.converters` | A [family converter](families.md#family-converters) for a format several datasets share | Core's cache, for a builder |
| `medomni.builders` | A [task builder](built-tasks.md#write-your-own-builder) | Studio |
| `medomni.caches` | A [cache backend](cache.md#backends) | Core's cache |
| `medomni.services` | A service a run starts beside the agent, such as Perception's perception service | Bench's agent runner |
| `medomni.arms` | An [arm](../bench/runs.md#arms) by name, and what the run attaches | Bench's agent runner |
| `medomni.arm_builds` | An arm's build side for one builder, named `<builder>:<arm>` | That builder |
| `medomni.tools` | A Studio tool of one kind | Studio |
| `medomni.runners` | The runner for one kind of intelligence | Bench |
| `medomni.metrics` | A metric a target may name | Bench's scorer |

- Bench, Perception and Studio register their own pieces in the same groups, such as Bench's four built-in arms and Studio's builder, `medomni-v1`.
- In v0.3.0, `medomni.runners` and `medomni.metrics` hold only MedOmni's own pieces: the agent runner, and `auc`, `qwk` and `mae`.

## Example

A package with a dataset, a task and a converter lists two entry points in its own `pyproject.toml`:

```toml
[project]
name = "medomni-myname"
dependencies = ["medomni>=0.3,<0.4"]

[project.entry-points."medomni.plugins"]
myname = "medomni_myname:content"

[project.entry-points."medomni.converters"]
my-format = "medomni_myname.converters:MyFormat"
```

After `pip install medomni-myname`, its dataset and task appear in Studio's commands.

Install the package as a wheel or in editable mode. Zip installs are not supported: they give no real folder, so hooks cannot load.

## How MedOmni loads them

- **Names.** Each piece is named `<package>:<name>`, such as `medomni-myname:my-task`. Built-in pieces use the package `medomni`.
- **Collisions.** A plug-in command that reuses a built-in command name is skipped with a warning, and the built-in runs. Two other pieces of one kind with the same name are both listed with an error, and neither is loaded.
- **Lazy loading.** At start, a command reads entry-point names and folder paths only. A piece is read or imported when a command first uses it.
- **Validation.** Each piece is checked against its [contract](contracts.md) when it is read. A piece that fails is listed with its error and not used.
- **Same as built-in.** A loaded piece works in every command as a built-in piece does.

```bash
medomni plugins
```

It reads every installed piece, checks it, and lists each package with what it adds and any errors.

## The testing kit

`medomni.core.testing` runs the same checks as MedOmni's CI. A plug-in package runs them in its own CI, so it passes the same checks as a pull request.

A plug-in's CI checks out MedOmni and installs it in editable mode (`uv pip install -e .`). MedOmni reads its built-in content (families, and Bench's, Perception's and Studio's content) only from a clone; outside one, it reads only plug-in folders.

<!-- outline (Stage 4 part 5), to be written when it is built:
- CI: what MedOmni's CI runs on every pull request (the tests, `medomni contracts check`, `medomni plugins`, the data check), and on which runner (D3).
- The data check: a new commit may hold no record id and no data file outside a testdata folder that carries a provenance and licence file.
- The example plug-in package, `medomni-example`: one task template on dummy data and one rule encoder; where it lives (D2); how its CI installs MedOmni and runs the testing kit; copy it to start a package.
- The testing kit's public names, as part 5 settles them.
-->

## Where it lives

- `src/medomni/core/plugins/`: finding content folders and entry points
- `src/medomni/core/testing/`: the check runner

## Where next

- [Extend MedOmni](../extend.md): every way to add to MedOmni.
- [Contribute](../../guides/contribute.md#publish-a-plug-in-package): publish a plug-in package step by step.
