# Get started

From install to a scored Bench run: first on dummy data, which needs no credentials, then on real data. To use only the encoders, see [Use the encoders](guides/use-the-encoders.md).

## Before you start

- Python 3.11 or later, Docker and [uv](https://docs.astral.sh/uv/).
- A model for your agent: a local model server, or an API key for a model provider.

## 1. Install

```bash
git clone --branch v0.3.0 https://github.com/medomni/MedOmni medomni && cd medomni
```

```bash
uv venv && source .venv/bin/activate && uv pip install -e .
```

```bash
medomni --version
```

MedOmni writes your configuration, built tasks, runs and results to the workspace: `~/.medomni`, or the folder in `MEDOMNI_HOME`. Nothing in it is committed or uploaded.

## 2. Describe your agent

Copy the agent template and set your model. See [Run your agent](guides/run-your-agent.md) for every field.

```bash
medomni bench agent new my-agent
```

## 3. Run on dummy data

Dummy data is generated from the dataset packages and each family's declared format. It needs no credentials and contains no patient values. To look at it, `medomni studio dummy <dataset> --out <dir>` writes one dataset's dummy data to a folder.

```bash
medomni studio task build --set medomni-bench/smoke-dummy
```

Studio's builder, `medomni-v1`, writes the set's built tasks to your workspace. Bench runs and scores them.

The set's arm gives the agent encoders, which run as images on your machine. Before the first run, build them:

- Each encoder you want the agent to have: `medomni perception check perception/encoders/<family>/<encoder> --record` builds its image, checks it on its test data and records it. The perception service serves only recorded images.
- Then the perception service, which carries the record:

    ```bash
    docker build -f src/medomni/perception/sidecar/Dockerfile -t medomni-perception .
    ```

    `medomni bench run` refuses to start without it and prints this command.

For a provider's API, export its key in the same shell first, such as `export OPENAI_API_KEY=...`.

```bash
medomni bench run --agent my-agent.yaml --set medomni-bench/smoke-dummy
```

`medomni bench run` runs every atom task in Harbor and records each run in its run folder.

## 4. Score

```bash
medomni bench score --set medomni-bench/smoke-dummy
```

It prints one row per task, target, agent and arm: the score, the number of patients and the failure rate. Scores on dummy data only show that the pipeline works.

## 5. Run on real data

MedOmni hosts no dataset. Download and connect each dataset as in [Connect your data](guides/connect-your-data.md), then build its task set as in [Rebuild a task set](guides/rebuild-a-task-set.md):

- **VitalDB** is open and needs no access request: `medomni-bench/vitaldb`.
- **MIMIC-IV, AI-READI and BDSP** need your own access: `medomni-bench/v1`.

## Where next

- [Run your agent](guides/run-your-agent.md): your own model, with and without encoders.
- [Concepts](learn/concepts.md): the terms used above.
