# Plug-ins

A plug-in package is an outside Python package, named `medomni-<name>`, that adds agents, dataset adapters, tasks or encoders to MedOmni without a pull request. MedOmni finds it through Python entry points.

Use a plug-in when the work should stay in your repository, for example tasks on data that cannot leave your institution.

## Entry-point groups

| Group | Registers | Same as in-repo |
|---|---|---|
| `medomni.agents` | An agent config | `bench/agents/` |
| `medomni.datasets` | A dataset adapter and its policy | `bench/datasets/<dataset>/` |
| `medomni.tasks` | A task spec | `bench/tasks/specs/` |
| `medomni.encoders` | A model card and its image | `perception/encoders/<family>/<encoder>/` |

```toml
[project.entry-points."medomni.tasks"]
my-task = "medomni_myname.tasks:SPEC"
```

## How MedOmni loads them

- At start, the `medomni` command reads every installed entry point in the four groups.
- Each piece is validated against its contract before use. A piece that fails is listed with its error and not loaded.
- Loaded pieces work in every command as built-in pieces do.

```bash
medomni plugins
```

It lists each installed package and what it adds.

## The testing kit

`medomni.core.testing` holds the checks behind every check command. A plug-in package runs them in its own CI, so it passes the same checks as a pull request.

## Where it lives

- `core/plugins/`: entry-point loading
- `core/testing/`: the shared checks

## Where next

- [Contribute](../../guides/contribute.md#publish-a-plug-in-package): publish a plug-in package step by step.
- [Contracts](contracts.md): what each piece is validated against.
