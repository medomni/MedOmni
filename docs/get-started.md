# Get started

From install to a scored Bench run: first on dummy data, which needs no credentials, then on real data. To use only the encoders, see [Use the encoders](guides/use-the-encoders.md).

## Before you start

- Python 3.10 or later, Docker and [uv](https://docs.astral.sh/uv/).
- A model for your agent: a local model server, or an API key for a model provider.

## 1. Install

```bash
git clone --branch v0.3.0 <repository-url> medomni && cd medomni
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
cp bench/templates/agent/agent.yaml my-agent.yaml
```

## 3. Run on dummy data

Dummy data is generated from each family's declared format. It needs no credentials and contains no patient values.

```bash
medomni bench task build --batch smoke-dummy
```

```bash
medomni bench run --agent my-agent.yaml --batch smoke-dummy
```

`medomni bench run` pulls the encoder images the tasks need, runs every atom task in Harbor and records each run in the results file.

## 4. Score

```bash
medomni bench score --batch smoke-dummy
```

It prints one row per task, target, agent and condition: the score, the number of patients and the failure rate. Scores on dummy data only show that the pipeline works.

## 5. Run on real data

- **VitalDB** is openly licensed. Build and run the `vitaldb` batch as above.
- **MIMIC-IV, AI-READI and BDSP** need your own access. Connect your copy and build the `v1-mini` batch, as in [Connect your data](guides/connect-your-data.md).

## Where next

- [Run your agent](guides/run-your-agent.md): your own model, with and without encoders.
- [Concepts](learn/concepts.md): the terms used above.
