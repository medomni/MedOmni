# Contribute

This guide is for contributors: you end up with a new task, agent config or encoder in the repository, checked by the same commands the team uses.

Each area of the repository has an owner who reviews changes to it; the repository README lists them.

## Add a task

For a task on MIMIC-IV, AI-READI or BDSP, using families MedOmni already declares.

### Before you start

- Access to the dataset, and its root set in `data_task/data_roots.yaml`.
- The task's inputs map to existing families. See [Families](../reference/families.md).

### Steps

1. Add the proposal as a row in `data_task/taskbuilder/intake/proposals.csv` (timestamp, proposer, org, dataset, title, statement, mode, target, streams, optional prediction time), then compile it into a draft spec.

    ```bash
    python data_task/taskbuilder/intake/compile.py data_task/taskbuilder/intake/proposals.csv
    ```

2. Resolve every item in the draft's `unresolved:` list, record the decisions in `data_task/taskbuilder/intake/resolutions/<task-id>.yaml`, and freeze the spec.

    ```bash
    python data_task/taskbuilder/intake/freeze.py <task-id>
    ```

3. Emit the task folder and validate it.

    ```bash
    python data_task/taskbuilder/emit.py data_task/taskbuilder/specs/<task-id>.yaml
    ```

4. To run the task type as atom tasks, add its targets to the atomic builder's census in `emit_atomic.py` and build it, as in [Connect your data](connect-your-data.md).
5. Pin the task into a batch. `pin_batch.py` rewrites the whole batch file from the task ids you list, so list every task the batch should hold. Task data stays local.

    ```bash
    python data_task/taskbuilder/pin_batch.py <batch> <task-id> [<task-id> ...]
    ```

### Check

```bash
python data_task/taskbuilder/validate.py data_task/taskbuilder/specs/<task-id>.yaml
```

It checks the spec's keys and metric, that the label derivation resolves, that no answers or leaking inputs reach `data/`, that staged files match their families, and that the folder matches its `FINGERPRINT`.

## Add an agent

For a new model or provider behind the `terminus-2` scaffold.

### Steps

1. Add `harness/harbor/agents/terminus-2-<name>.yaml` with the model name, the key as a `${VARNAME}` reference, and `max_turns: 300`. See [Run your agent](run-your-agent.md).
2. Probe the model, then add it to `harness/models.yaml` with the name the provider actually serves.

### Check

`python harness/build.py emit <experiment>` dry-runs the first job in Harbor and prints `dry-run OK` or the error.

## Add an encoder

### Before you start

- The encoder reads one existing family. Its code, weights and test data have licenses that allow you to package them.
- Test data for the family: synthetic or openly licensed, with a provenance note.

### Steps

1. Create the encoder's folder by adapting the nearest existing encoder:

    ```text
    perception/encoders/<family>/<encoder>/
    ├── adapter.py
    ├── card.yaml
    ├── demo.py
    ├── Dockerfile
    └── testdata/
        ├── input.*
        ├── expected.json
        └── PROVENANCE.md
    ```

2. Implement `FAMILY` and `encode(sample, options)` in `adapter.py`, with expensive set-up in `load()`. Build the Dockerfile on the shared runtime and pin the base image, dependencies, source revision and weight hashes.
3. Write the model card. It declares the family, outputs, options, license and source; see [Encoders](../reference/encoders.md).
4. Build the image, record its expected responses, and regenerate the encoder index.

    ```bash
    uv run perception/registry.py build <family>__<encoder>
    ```

    ```bash
    uv run perception/registry.py freeze --docker <family>__<encoder>
    ```

    ```bash
    uv run perception/registry.py index
    ```

`perception/AGENTS.md` has the full onboarding notes.

### Check

```bash
uv run perception/registry.py validate <family>__<encoder>
```

```bash
uv run perception/registry.py test --docker <family>__<encoder>
```

```bash
uv run perception/registry.py plan <family>__<encoder>
```

`validate` checks the model card against the schema and the family registry; `test` runs the built image on its test data and compares the responses with `expected.json`; `plan` should report the encoder as runnable.

## Where next

- [Tasks](../reference/tasks.md): the spec format.
- [Design principles](../learn/principles.md): including the rules for editing these docs.
