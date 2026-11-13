# Contribute

For contributors who add an agent to Bench, a dataset or a task to Studio, or an encoder to Perception.

## How MedOmni is developed

MedOmni is developed in a private repository. The public repository is an export of each release, and every commit in it keeps its author.

A pull request goes to the public repository:

1. Create the starting files with the piece's `new` command, fill them in, and run its check command locally.
2. Open a pull request on the public repository. CI runs the same check, and the MedOmni team reviews it.
3. Once it is merged there, it is brought into development under your name and ships in the next release.

Work that should stay in your own repository, for example a task on data that cannot leave your institution, can be a plug-in package instead: your own `medomni-*` package that ships the same pieces in a content folder and runs the same check. See [Publish a plug-in package](#publish-a-plug-in-package).

Contributions change only extension points. Only the MedOmni team changes Core and the contracts; if you need a contract change, such as a new family, open an issue first.

Every model card and task template lists its `authors`.

## What you can add

- [Add an encoder](add-an-encoder.md): a new encoder for an existing family.
- [Add a dataset](add-a-dataset.md): a new openly licensed dataset, read by MedOmni's builder.
- [Add a task](add-a-task.md): a template and a cohort on a supported dataset.
- An agent, below.

## Add an agent (Bench)

For a new scaffold or model.

### Steps

1. Create the agent config and fill it in, as in [Test your agent](test-your-agent.md).

    ```bash
    medomni bench agent new my-agent
    ```

2. Open a pull request adding it as `bench/agents/<name>.yaml`.

### Check

```bash
medomni bench run --agent my-agent.yaml --set medomni-bench/smoke-dummy
```

Every atom task of `medomni-bench/smoke-dummy` must finish with a run and no infrastructure error.

## Publish a plug-in package

For agents, datasets, tasks or encoders that live in your own repository.

### Steps

1. Create a Python package named `medomni-<name>` that depends on `medomni`.
2. Add a content folder to the package, laid out like MedOmni's repository: `bench/agents/`, `studio/datasets/<dataset>/`, `bench/benchmarks/<benchmark>/`, `perception/encoders/<family>/<encoder>/`. Create each piece in it as on the Add pages.
3. Register the folder with one entry point in `pyproject.toml`:

    ```toml
    [project.entry-points."medomni.plugins"]
    myname = "medomni_myname:content"
    ```

    A family converter, a task builder, an arm or a Studio tool is Python code: register it in `medomni.converters`, `medomni.builders`, `medomni.arms` (with its build side in `medomni.arm_builds`) or `medomni.tools`. A converter for one dataset's own format is declared in its `dataset.yaml` instead. See [Plug-ins](../learn/core/plugins.md#python-pieces).

4. In your package's tests, run the same checks with `medomni.core.testing`.
5. Install it as a wheel or in editable mode. Zip installs are not supported.

### Check

```bash
medomni plugins
```

Your package and each piece it adds are listed, and the check commands (`medomni studio task check`, `medomni perception check` and the rest) work on them as on built-in pieces.

<!-- outline (Stage 4 part 5): "What CI checks on your pull request": the checks above run in CI, plus the data check (no record id, no data file outside a testdata folder with provenance and licence). Point to the example plug-in package as the starting copy for a plug-in. -->

## Where next

- [Design principles](../learn/principles.md): what Core and the extension points are.
- [Tasks](../reference/tasks.md): the task template contract.
- [Recipes](../reference/recipes.md): the cohort, label and evidence fields.
