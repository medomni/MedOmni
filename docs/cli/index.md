# Commands

v0.2.0 has no single command. Each step is a script, run from the repository root; this page lists them in the order a run uses them.

## Build tasks

| Command | Does |
|---|---|
| `python data_task/taskbuilder/emit_atomic.py <type> [...] --variant <v> --batch <b> -n <N>` | Builds atom tasks: one per task type and patient, in one condition (`enc`, `noenc`, `enc-forced`). `--all` takes every type; `--seed` fixes the patients; `--ladder` builds the modality-ladder rungs. |
| `python data_task/taskbuilder/emit.py data_task/taskbuilder/specs/<id>.yaml` | Emits a spec's task folder into `data_task/tasks/<id>/`. |
| `python data_task/taskbuilder/validate.py data_task/taskbuilder/specs/<id>.yaml` | Checks a spec and its emitted folder; JSON report, exit 1 on any failure. |
| `python data_task/taskbuilder/pin_batch.py <batch> [<id> ...]` | Writes a batch file from the listed tasks' fingerprints. |
| `python data_task/taskbuilder/intake/compile.py <csv>` | Turns proposal rows into draft specs. |
| `python data_task/taskbuilder/intake/freeze.py <id>` | Freezes a resolved draft spec. |
| `python data_task/taskbuilder/family_audit.py audit` | Checks the family registry and its samples. |

## Run and score

| Command | Does |
|---|---|
| `python harness/build.py emit <experiment>` | Turns `harness/experiments/<experiment>.yaml` into one Harbor job per agent × condition × repetition, writes a prerun sheet per job, and dry-runs the first. |
| `harbor run -c harness/harbor/base.yaml -c harness/harbor/agents/<agent>.yaml -c harness/harbor/jobs/<job>.yaml` | Runs one job. Printed verbatim in the job's prerun sheet. |
| `python harness/build.py import runs/experiments/<experiment>/jobs/<job>` | Writes one record per run to the results file. `--new-ledger` creates the file the first time. |
| `python harness/build.py status <experiment>` | Shows which patients of each task type have a run. |
| `python harness/score.py [--experiment <experiment>]` | Scores every complete task type per agent, condition and repetition. The only script that writes scores. `--dry-run` shows what it would score; `--force` re-scores under the current metrics. |
| `python harness/analyze.py grid <experiment>` | Writes the task × agent × condition table to `runs/experiments/<experiment>/analysis/grid.md`. |

## Encoders

| Command | Does |
|---|---|
| `uv run perception/registry.py plan [<id> ...]` | Status of every encoder: runnable, unbuilt, stale, failing or retired. |
| `uv run perception/registry.py build [<id> ...]` | Builds encoder images, tagged `:dev`. |
| `uv run perception/registry.py validate [<id> ...]` | Checks model cards against the schema and the family registry. |
| `uv run perception/registry.py test --docker [<id> ...]` | Runs built images on their test data and compares with `expected.json`. |
| `uv run perception/registry.py freeze --docker [<id> ...]` | Records `expected.json` from the current responses. |
| `uv run perception/registry.py index` | Regenerates `perception/encoders.yaml`. |
| `uv run perception/gateway/main.py --data-root <dir>` | Starts the gateway on `127.0.0.1:8000`. |
| `docker build -f harness/perception-image/Dockerfile -t medomni-perception .` | Builds the perception sidecar used inside tasks. |

## Tests

| Command | Does |
|---|---|
| `python3 -m unittest discover -s harness/tests` | The harness gates, Assurance's mutation tests and the sidecar guard tests. |

## Where next

- [Get started](../get-started.md): the commands in order on a first run.
- [Architecture](../learn/architecture.md): where each script sits.
