# Plug-ins

MedOmni loads its own projects and outside packages the same way: through Python entry points. Core imports no project.

## Projects

- Each project registers itself in the `medomni.projects` entry-point group.
- A project registers three kinds of piece with Core:
    - its subcommands, such as `medomni bench …`
    - the checks behind its check commands
    - its audit checks
- Bench and Perception are registered by MedOmni's own `pyproject.toml`. A later project joins the same way.

## Plug-in packages

A plug-in package is an outside Python package, named `medomni-<name>`, that adds agents, dataset adapters, tasks or encoders without a pull request. Use one when the work should stay in your repository, for example tasks on data that cannot leave your institution.

| Group | Registers | Owned by | Same as in-repo |
|---|---|---|---|
| `medomni.agents` | An agent config | Bench | `bench/agents/` |
| `medomni.datasets` | A dataset adapter and its policy | Bench | `src/medomni/bench/datasets/<dataset>/` |
| `medomni.tasks` | A task spec | Bench | `bench/specs/` |
| `medomni.encoders` | A model card and its image | Perception | `perception/encoders/<family>/<encoder>/` |

```toml
[project.entry-points."medomni.tasks"]
my-task = "medomni_myname.tasks:SPEC"
```

## How MedOmni loads them

- **Names.** Each piece is named `<package>:<name>`. Built-in pieces use the package `medomni`.
- **Collisions.** Two pieces with the same name: both are listed with an error, and neither is loaded.
- **Lazy loading.** At start, the command reads the entry-point names only. A piece is imported when a command first uses it.
- **Validation.** On import, each piece is validated against its contract. A piece that fails is listed with its error and not used.
- **Same as built-in.** A loaded piece works in every command as a built-in piece does.

```bash
medomni plugins
```

It imports every installed piece, validates it, and lists each package with what it adds and any errors.

## The testing kit

`medomni.core.testing` runs the checks the projects register. A plug-in package runs them in its own CI, so it passes the same checks as a pull request.

## Where it lives

- `src/medomni/core/plugins/`: entry-point loading
- `src/medomni/core/testing/`: the check runner

## Where next

- [Contribute](../../guides/contribute.md#publish-a-plug-in-package): publish a plug-in package step by step.
- [Contracts](contracts.md): what each piece is validated against.
