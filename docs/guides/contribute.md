# Contribute

For contributors who add an agent, dataset adapter or task to Bench, or an encoder to Perception.

There are two routes. Both run the same check.

- **Pull request.** Start from the template, fill it in, run its check command locally, and open a pull request; CI runs the same check.
- **Plug-in package.** Publish your own `medomni-*` package that registers the same pieces through entry points. Use this when your work should stay in your own repository, for example a task on data that cannot leave your institution. See [Publish a plug-in package](#publish-a-plug-in-package).

Contributions change only extension points. Only the MedOmni team changes Core and the contracts; if you need a contract change, such as a new family, open an issue first.

Every model card and task spec lists its `authors`.

## Add an agent (Bench)

For a new scaffold or model.

### Steps

1. Copy `bench/templates/agent/agent.yaml` and fill it in, as in [Run your agent](run-your-agent.md).
2. Open a pull request adding it as `bench/agents/<name>.yaml`.

### Check

```bash
medomni bench run --agent my-agent.yaml --batch smoke-dummy
```

Every atom task of `smoke-dummy` must finish with a run and no infrastructure error.

## Add a dataset adapter (Bench)

For a new openly licensed dataset, such as VitalDB. Pull requests add tasks only on openly licensed datasets; use a plug-in package for others.

### Before you start

- The dataset's license allows redistribution of samples (for example CC BY 4.0).
- Its signals map to existing families. See [Families](../reference/families.md).

### Steps

1. Copy the template into the package:

    ```bash
    cp -r bench/templates/dataset bench/datasets/my-dataset
    ```

2. Implement the adapter: locate the dataset on disk, survey what each patient has, and extract the files a task needs.
3. Write the dataset policy from the license: what may be published and which routes may see the data. See [Datasets](../reference/datasets.md).
4. Upload a small data sample to the MedOmni task-samples repository on Hugging Face.
5. Add at least one task on the dataset, as below, and open a pull request.

### Check

```bash
medomni bench data check my-dataset
```

It runs the adapter on the data sample and validates the policy. Check the dataset's tasks with `medomni bench task check`, as below.

## Add a task (Bench)

For a task on a supported dataset, using families MedOmni already declares.

### Steps

1. Create the spec from the template:

    ```bash
    medomni bench task new vitaldb_my-task --dataset vitaldb
    ```

2. Fill in the spec: the question, the target and its metric, the cohort, the prediction time and the allowed evidence. Inputs that would leak the target are banned automatically; do not list them. The fields are in [Tasks](../reference/tasks.md).
3. Build the task on dummy data and on the real dataset, and open a pull request with the spec.

### Check

```bash
medomni bench task check bench/tasks/specs/vitaldb_my-task.yaml
```

It checks:

- the spec's fields and metric
- that the target derivation resolves
- that no answers or leaking inputs reach the agent
- that staged files match their families
- that the built task matches its fingerprint

## Add an encoder (Perception)

Encoder folders live in `perception/encoders/` and are built into images; they are not part of the installed package.

### Before you start

- The encoder reads one existing family. Its code, weights and test data have licenses that allow you to package them.
- Test data for the family: synthetic or openly licensed, with a provenance note.

### Steps

1. Copy `perception/templates/encoder/` to a new folder:

    ```text
    perception/encoders/<family>/<encoder>/
    ├── adapter.py
    ├── card.yaml
    ├── Dockerfile
    └── testdata/
        ├── input.*
        ├── expected.json
        └── PROVENANCE.md
    ```

2. Implement the adapter and pin the image:
    - `encode(sample, options)` in `adapter.py`, with expensive set-up in `load()`
    - base image, dependencies, source revision and weight hashes pinned in the Dockerfile
3. Write the model card: the family, outputs, options, license and source. See [Encoders](../reference/encoders.md).
4. Record the expected responses on the test data, and open a pull request.

    ```bash
    medomni perception check perception/encoders/<family>/<encoder> --freeze
    ```

### Check

```bash
medomni perception check perception/encoders/<family>/<encoder>
```

It validates the model card against its contract and the family registry, builds the image, runs it on the test data and compares the responses with `expected.json`. GPU encoders may run on a self-hosted runner.

## Publish a plug-in package

For agents, dataset adapters, tasks or encoders that live in your own repository.

### Steps

1. Create a Python package named `medomni-<name>` that depends on `medomni`.
2. Build each piece from its template, as in the sections above.
3. Register each piece under its entry-point group in `pyproject.toml`: `medomni.agents`, `medomni.datasets`, `medomni.tasks` or `medomni.encoders`.

    ```toml
    [project.entry-points."medomni.tasks"]
    my-task = "medomni_myname.tasks:SPEC"
    ```

4. In your package's tests, run the same checks with `medomni.core.testing`.

### Check

```bash
medomni plugins
```

Your package and each piece it adds are listed, and the commands above (`medomni bench task check`, `medomni perception check` and the rest) work on them as on built-in pieces.

## Where next

- [Design principles](../learn/principles.md): what Core and the extension points are.
- [Tasks](../reference/tasks.md): the task spec contract.
