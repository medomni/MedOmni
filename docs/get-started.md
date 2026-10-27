# Get started

This page takes you from a fresh checkout to a scored experiment: two patients on one task type, one agent, one repetition.

## Before you start

- Linux with Docker, and Python 3 with [uv](https://docs.astral.sh/uv/).
- The [Harbor](https://github.com/laude-institute/harbor) CLI. The team runs 0.23.0.
- Access to the MedOmni repository, and to at least one dataset under its own license: MIMIC-IV, AI-READI or BDSP. See [Datasets](catalog/datasets.md).
- An ext4 disk for `runs/`. Harbor sets file permissions on trial folders, which exFAT cannot do.
- An API key for the agent's model.

## 1. Check out v0.2.0

```bash
git clone https://github.com/BosonHwang/MedOmni.git
```

```bash
cd MedOmni && git checkout v0.2.0
```

## 2. Set up Python

The harness needs PyYAML; the task builder also reads clinical file formats. One environment, kept outside the checkout, covers both:

```bash
uv venv ~/.venvs/medomni
```

```bash
source ~/.venvs/medomni/bin/activate && uv pip install pyyaml numpy pandas pydicom pyedflib h5py pillow wfdb
```

Every `python` command in these docs runs in this environment. Commands that start with `uv run` bring their own dependencies.

## 3. Point MedOmni at your machine

Machine settings live in two files. Neither holds task content.

- `data_task/data_roots.yaml`: where each dataset is on disk, one line per dataset (`mimic`, `aireadi`, `bdsp`).
- `harness/config.yaml`: where runs are written (`runs_root`) and where your API keys file is (`keys_file`, default `harness/api-keys.env`).

Put your keys in the keys file in dotenv form, for example `DEEPSEEK_API_KEY=...`. Never commit it.

!!! warning "Machine-specific paths in v0.2.0"
    Two paths are written for the team's machine and need editing on yours: `jobs_dir` in `harness/harbor/base.yaml`, and `BRIDGE_CACHE` near the top of `data_task/taskbuilder/emit_atomic.py`.

## 4. Build the images

The gateway sidecar that serves encoders inside each task:

```bash
docker build -f harness/perception-image/Dockerfile -t medomni-perception .
```

The encoder images the task needs. Each is built locally and tagged `:dev`:

```bash
uv run perception/registry.py build cxr-radiograph-2d__torchxrayvision
```

```bash
uv run perception/registry.py plan
```

`plan` shows every encoder as runnable, unbuilt, stale, failing or retired.

## 5. Build atom tasks

An atom task is one task for one patient. This builds two atoms of one MIMIC-IV task type, in the encoder arm:

```bash
python data_task/taskbuilder/emit_atomic.py mimic_icu-stay-radiology --variant enc --batch smoke -n 2
```

The atoms land in `data_task/atomtasks/`, with the parent task's cohort, gold answers and fingerprint in `data_task/atomtasks/_parents/mimic_icu-stay-radiology/`. Both stay on your machine.

## 6. Declare an experiment

An experiment is one yaml file in `harness/experiments/`. Save this as `harness/experiments/my-first.yaml`:

```yaml
experiment: my-first
tier: SMOKE
description: two atoms of one type, encoder arm, one rep
generation: fix-smoke
types: [mimic_icu-stay-radiology]
variants: {enc: data_task/atomtasks}
agents: [terminus-2]
reps: [1]
expect: {terminus-2: {model_served: deepseek-flash}}
```

`generation` must match the atoms you built (`fix-smoke` is the builder's default). `expect.model_served` is the model name the provider reports back; a run that reports any other name is failed at import.

## 7. Run it

1. Emit the job. This writes a Harbor job overlay, pre-mints the run ids, writes a prerun sheet to `harness/prerun/`, and dry-runs the job in Harbor.

    ```bash
    python harness/build.py emit my-first
    ```

2. Read the prerun sheet and sign its approval block.
3. Load your keys and run the `harbor run` command printed in the sheet. It has this shape:

    ```bash
    set -a; source harness/api-keys.env; set +a
    ```

    ```bash
    harbor run -c harness/harbor/base.yaml -c harness/harbor/agents/terminus-2.yaml -c harness/harbor/jobs/<job>.yaml
    ```

    The sheet also prints `harness/docker_hygiene.py` lines before and after the run. That script is not in v0.2.0; skip those lines.

4. Import the job into the ledger, score it, and print the table.

    ```bash
    python harness/build.py import runs/experiments/my-first/jobs/<job>
    ```

    ```bash
    python harness/score.py --experiment my-first
    ```

    ```bash
    python harness/analyze.py grid my-first
    ```

## Check

`analyze.py grid` prints one row per task type with the score, the number of atoms and the failure rate, and writes it to `runs/experiments/my-first/analysis/grid.md`. Two patients give a number that means nothing clinically; it shows the pipeline works.

## Where next

- [Run your agent](guides/run-your-agent.md): your own model, more types, both arms.
- [Concepts](learn/concepts.md): what a task, an atom task and a generation are.
- [Commands](cli/index.md): every script used above.
