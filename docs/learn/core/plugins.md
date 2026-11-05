# Plug-ins

A plug-in package is an outside Python package, named `medomni-<name>`, that adds agents, datasets, tasks, encoders or Studio tools without a pull request. Use one when the work should stay in your repository, for example tasks on data that cannot leave your institution. [Extend MedOmni](../extend.md) compares it with the other ways to add things.

## Register pieces

A package registers each piece in the entry-point group for its kind. It does not register with Bench or Perception: MedOmni sends each kind to the project that uses it.

| Group | Registers | Used by | Same as in-repo |
|---|---|---|---|
| `medomni.agents` | An agent config | Bench | `bench/agents/` |
| `medomni.datasets` | A dataset package, with its policy | Bench | `bench/datasets/<dataset>/` |
| `medomni.tasks` | A task template and its cohorts | Bench | `bench/datasets/<dataset>/tasks/<template>/` |
| `medomni.encoders` | A model card and its image | Perception | `perception/encoders/<family>/<encoder>/` |
| `medomni.tools` | A Studio tool of one kind | Studio | `src/medomni/studio/<kind>/` |

One package can add several kinds. A package with a task and an encoder lists both in its own `pyproject.toml`:

```toml
[project]
name = "medomni-myname"
dependencies = ["medomni>=0.3,<0.4"]

[project.entry-points."medomni.tasks"]
my-task = "medomni_myname.tasks:MY_TASK"

[project.entry-points."medomni.encoders"]
my-encoder = "medomni_myname.encoders:CARD"
```

After `pip install medomni-myname`, `my-task` appears in Bench's commands and `my-encoder` in Perception's.

## How MedOmni loads them

- **Names.** Each piece is named `<package>:<name>`, such as `medomni-myname:my-task`. Built-in pieces use the package `medomni`.
- **Collisions.** Two pieces with the same name: both are listed with an error, and neither is loaded.
- **Lazy loading.** At start, a command reads the entry-point names only. A piece is imported when a command first uses it.
- **Validation.** On import, each piece is checked against its [contract](contracts.md). A piece that fails is listed with its error and not used.
- **Same as built-in.** A loaded piece works in every command as a built-in piece does.

```bash
medomni plugins
```

It imports every installed piece, checks it, and lists each package with what it adds and any errors.

## The testing kit

`medomni.core.testing` runs the same checks as MedOmni's CI. A plug-in package runs them in its own CI, so it passes the same checks as a pull request.

## Where it lives

- `src/medomni/core/plugins/`: entry-point loading
- `src/medomni/core/testing/`: the check runner

## Where next

- [Extend MedOmni](../extend.md): every way to add to MedOmni.
- [Contribute](../../guides/contribute.md#publish-a-plug-in-package): publish a plug-in package step by step.
