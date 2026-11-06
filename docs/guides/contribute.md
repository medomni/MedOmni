# Contribute

For contributors who add an agent, a dataset or a task to Bench, or an encoder to Perception.

There are two routes. Both run the same check.

- **Pull request.** Create the starting files with the piece's `new` command, fill them in, run its check command locally, and open a pull request; CI runs the same check.
- **Plug-in package.** Publish your own `medomni-*` package that ships the same pieces in a content folder. Use this when your work should stay in your own repository, for example a task on data that cannot leave your institution. See [Publish a plug-in package](#publish-a-plug-in-package).

Contributions change only extension points. Only the MedOmni team changes Core and the contracts; if you need a contract change, such as a new family, open an issue first.

Every model card and task template lists its `authors`.

## Add an agent (Bench)

For a new scaffold or model.

### Steps

1. Create the agent config and fill it in, as in [Run your agent](run-your-agent.md).

    ```bash
    medomni bench agent new my-agent
    ```

2. Open a pull request adding it as `bench/agents/<name>.yaml`.

### Check

```bash
medomni bench run --agent my-agent.yaml --set smoke-dummy
```

Every atom task of `smoke-dummy` must finish with a run and no infrastructure error.

## Add a dataset (Bench)

For a new openly licensed dataset, such as VitalDB. Pull requests add datasets only when openly licensed; use a plug-in package for others.

### Before you start

- The dataset's license allows redistribution of samples (for example CC BY 4.0).
- Its recordings map to existing families. See [Families](../reference/families.md).

### Steps

1. Create the dataset package:

    ```bash
    medomni bench data new my-dataset
    ```

2. Write `dataset.yaml`: the description (unit, kind of time, version), the format readers and what each reads, and the dataset's rules. See [Datasets reference](../reference/datasets.md#dataset-package).
3. List every code the dataset emits in `codes.csv`. Use the [shared codes](../reference/recipes.md#shared-codes) where the dataset has those concepts.
4. Write `labels.yaml` and `evidence.yaml`. See [Recipes reference](../reference/recipes.md).
5. Write the dataset policy from the license: what may be published and which routes may see the data.
6. Upload a small data sample to the MedOmni task-samples repository on Hugging Face.
7. Add at least one template and cohort, as below, and open a pull request.

Python goes only in `hooks/`, for a label no rule can express. A file format no format reader knows needs a new format reader in Core: open an issue first.

### Check

```bash
medomni bench data check my-dataset
```

It loads the data sample and dummy data, checks that every code is in `codes.csv`, and validates the policy.

## Add a template and a cohort (Bench)

For a task on a supported dataset, using labels and families MedOmni already has, or labels you add to the dataset's library.

### Steps

1. Create the template and a first cohort:

    ```bash
    medomni bench task new vitaldb_my-task --dataset vitaldb
    ```

2. Fill in `template.yaml`: the question, the targets with each one's label and metric, the input and the variants. The labels' guards remove leaking evidence; do not list it again. The fields are in [Tasks reference](../reference/tasks.md#task-template).
3. Write a cohort in `cohorts/`: source population, prediction time, requirements and draw. Add its test patients. See [Recipes reference](../reference/recipes.md#cohort-file).
4. Preview the counts on your copy, adjust the cohort, then build.

    ```bash
    medomni studio preview vitaldb_my-task@n20
    medomni bench task build vitaldb_my-task@n20
    ```

5. Open a pull request with the template folder.

### Check

```bash
medomni bench task check vitaldb_my-task@n20
```

It checks:

- the template's fields and metrics
- that each target's label is in the library and states its window
- that the cohort's test patients give their expected results
- that no answers or guarded evidence reach the agent
- that staged files match their families
- that an agent submitting the true answers scores perfectly, and one giving the same answer every time scores at chance
- that the build matches its fingerprint

## Add an encoder (Perception)

Encoder folders live in `perception/encoders/` and are built into images; they are not part of the installed package.

### Before you start

- The encoder reads one existing family. Its code, weights and test data have licenses that allow you to package them.
- Test data for the family: synthetic or openly licensed, with a provenance note.

### Steps

1. Create the encoder folder:

    ```bash
    medomni perception new <family>/<encoder>
    ```

    It writes:

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

For agents, datasets, tasks or encoders that live in your own repository.

### Steps

1. Create a Python package named `medomni-<name>` that depends on `medomni`.
2. Add a content folder to the package, laid out like MedOmni's repository: `bench/agents/`, `bench/datasets/<dataset>/`, `perception/encoders/<family>/<encoder>/`. Create each piece in it as in the sections above.
3. Register the folder with one entry point in `pyproject.toml`:

    ```toml
    [project.entry-points."medomni.plugins"]
    myname = "medomni_myname:content"
    ```

    A family converter or a Studio tool is Python code: register it in `medomni.converters` or `medomni.tools`. See [Plug-ins](../learn/core/plugins.md#python-pieces).

4. In your package's tests, run the same checks with `medomni.core.testing`.
5. Install it as a wheel or in editable mode. Zip installs are not supported.

### Check

```bash
medomni plugins
```

Your package and each piece it adds are listed, and the commands above (`medomni bench task check`, `medomni perception check` and the rest) work on them as on built-in pieces.

## Where next

- [Design principles](../learn/principles.md): what Core and the extension points are.
- [Tasks](../reference/tasks.md): the task template contract.
- [Recipes](../reference/recipes.md): the cohort, label and evidence fields.
