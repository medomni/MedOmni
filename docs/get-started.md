# Get started

This page takes you from a checkout to a scored experiment: two patients, one task type, one agent.

## Before you start

- Docker, [uv](https://docs.astral.sh/uv/) and the [Harbor](https://github.com/laude-institute/harbor) CLI (0.23.0).
- Licensed access to at least one dataset. See [Datasets](reference/datasets.md).
- An API key for the agent's model.

## 1. Set up

Check out the tag and create a Python environment outside the checkout:

```bash
git checkout v0.2.0
```

```bash
uv venv ~/.venvs/medomni && source ~/.venvs/medomni/bin/activate && uv pip install pyyaml numpy pandas pydicom pyedflib h5py pillow wfdb
```

Every `python` command below runs in this environment.

## 2. Configure

| File | Set |
|---|---|
| `data_task/data_roots.yaml` | Where each dataset is (`mimic`, `aireadi`, `bdsp`). |
| `harness/config.yaml` | Where runs are written (`runs_root`) and your keys file (`keys_file`). |
| keys file | Your API key in dotenv form, for example `DEEPSEEK_API_KEY=...`. Never commit it. |

v0.2.0 also hard-codes one path that you must change: `BRIDGE_CACHE` in `data_task/taskbuilder/emit_atomic.py`.

## 3. Build images

The perception sidecar, and the encoders your task needs:

```bash
docker build -f harness/perception-image/Dockerfile -t medomni-perception .
```

```bash
uv run perception/registry.py build cxr-radiograph-2d__torchxrayvision
```

## 4. Build tasks

Two patients of one MIMIC-IV task type, with encoders available:

```bash
python data_task/taskbuilder/emit_atomic.py mimic_icu-stay-radiology --variant enc --batch smoke -n 2
```

The tasks land in `data_task/atomtasks/` and stay on your machine.

## 5. Run

Save this as `harness/experiments/my-first.yaml`:

```yaml
experiment: my-first
tier: SMOKE
description: two patients, one task type, with encoders
generation: fix-smoke
types: [mimic_icu-stay-radiology]
variants: {enc: data_task/atomtasks}
agents: [terminus-2]
reps: [1]
expect: {terminus-2: {model_served: deepseek-flash}}
```

`expect.model_served` is the model name the provider reports back; a run that reports another name is recorded as an error and never scored.

Emit the job. This dry-runs it and writes a prerun sheet to `harness/prerun/` with the exact `harbor run` command:

```bash
python harness/build.py emit my-first
```

Load your keys and run that command:

```bash
set -a; source harness/api-keys.env; set +a
```

```bash
harbor run -c harness/harbor/base.yaml -c harness/harbor/agents/terminus-2.yaml -c harness/harbor/jobs/<job>.yaml
```

The sheet also prints `harness/docker_hygiene.py` lines. That script is not in v0.2.0; skip them.

## 6. Score

```bash
python harness/build.py import runs/experiments/my-first/jobs/<job>
```

```bash
python harness/score.py --experiment my-first
```

```bash
python harness/analyze.py grid my-first
```

The last command prints one row per task type (score, patients, failure rate) and writes it to `runs/experiments/my-first/analysis/grid.md`. Two patients only show that the pipeline works; the number means nothing clinically.

## Where next

- [Run your agent](guides/run-your-agent.md): your own model, more task types, with and without encoders.
- [Concepts](learn/concepts.md): the terms used above.
