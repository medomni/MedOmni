"""`medomni studio task`: write a template to fill in, build a pair or a published set, check them (R-142)."""
from __future__ import annotations

import re
import sys

import yaml

def _set(name: str):
    from medomni.core.tasks.sets import load_set

    task_set, _ = load_set(name)
    return [e.task for e in task_set.tasks], list(task_set.arms), task_set.builder


def build(pair, set_name, arm, stream=None) -> int:
    """A pair with MedOmni's v1 builder, or a published set with the builder it names."""
    from medomni.core.builders import builder
    from medomni.core.tasks import TaskError
    from medomni.studio.build import BUILDER, build as run

    stream = stream or sys.stdout
    if bool(pair) == bool(set_name):
        print("name one pair or one --set", file=stream)
        return 2
    try:
        if set_name:
            pairs, arms, name = _set(set_name)
            if arm and set(arm) - set(arms):
                print(f"{set_name} does not list arm {sorted(set(arm) - set(arms))}", file=stream)
                return 1
            arms = arm or arms
        else:
            pairs, arms, name = [pair], arm or ["encoders"], BUILDER
        if name == BUILDER:
            run(pairs, arms, stream=stream)
        else:
            builder(name).build(pairs, arms, None)
    except (TaskError, FileNotFoundError) as e:
        print(f"build refused: {e}", file=stream)
        return 1
    return 0


def check(pair, set_name, release, stream=None) -> int:
    from medomni.studio.build import BuildError, run_checks

    stream = stream or sys.stdout
    try:
        problems = _release() if release else _check_set(set_name) if set_name else run_checks(pair) if pair else None
    except (BuildError, FileNotFoundError) as e:
        print(e, file=stream)
        return 1
    if problems is None:
        print("name a pair (<template>@<cohort>), --set <benchmark>/<set> or --release", file=stream)
        return 2
    for p in problems:
        print(f"  {p}", file=stream)
    print(f"{release and 'release' or set_name or pair}: {'ok' if not problems else f'{len(problems)} problem(s)'}", file=stream)
    return 1 if problems else 0


def _check_set(name: str) -> list[str]:
    from medomni.studio.build import run_checks
    from medomni.core.tasks.sets import load_set
    from medomni.studio.build.sets import package_of, pin_problems

    task_set, _ = load_set(name)

    def cohort_text(pair):
        package, template_id, cohort = package_of(pair)
        p = package / "tasks" / template_id / "cohorts" / f"{cohort}.yaml"
        return p.read_text(encoding="utf-8") if p.is_file() else None

    out = pin_problems(task_set, cohort_text)
    for e in task_set.tasks:
        if e.version:  # imported v0.2 sets (version 0) have no build here
            out += run_checks(e.task, arm_names=list(task_set.arms))
    return out


def _release() -> list[str]:
    """Every pinned pair in every set: config files against the last release tag, never data (R-111)."""
    from medomni.core import plugins
    from medomni.studio.build import sets

    repo = plugins.find_repo()
    read = sets.git_reader(repo, sets.last_release(repo))
    return [p for name, task_set in sets.all_sets() for p in sets.release_problems(task_set, name, sets.package_of, read)]


TEMPLATE = """\
# A new task template: fill in every field (Tasks reference page). Then write a label in labels.yaml and build it.
template_id: {id}
dataset: {dataset}
authors:
- {{name: <your name>, github: <your handle>}}
targets:
- {{name: <target>, label: '{dataset}:<label>', metric: auc}}
input: {{note: <what the proposal says the agent needs>}}
agent:
  statement: <the question, in one sentence>
  instruction: <what the prediction time means for this task>
  environment: {{cpus: 4, memory_mb: 8192, allow_internet: true, agent_timeout_sec: 1200, verifier_timeout_sec: 300}}
  submission_path: /workspace/submission/predictions.csv
"""
COHORT = """\
# A cohort (Recipes reference page). Each change to who, when or which answer raises the version.
version: '1.0'
source: {{}}
anchor: {{event: <an anchor code>}}
select: {{n: 20, by: [<target>], seed: {seed!r}}}
"""


def new(template: str, dataset: str, stream=None) -> int:
    from medomni.core.loading import find_package

    stream = stream or sys.stdout
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", template):
        print(f"'{template}' is not a template name (lower case, digits, hyphens)", file=stream)
        return 1
    try:
        package = find_package(dataset)
    except FileNotFoundError as e:
        print(e, file=stream)
        return 1
    folder = package / "tasks" / f"{dataset}_{template}"
    if folder.exists():
        print(f"{folder} already exists", file=stream)
        return 1
    (folder / "cohorts").mkdir(parents=True)
    (folder / "template.yaml").write_text(TEMPLATE.format(id=f"{dataset}_{template}", dataset=dataset), encoding="utf-8")
    (folder / "cohorts/n20.yaml").write_text(COHORT.format(seed=template), encoding="utf-8")
    print(f"wrote {folder}", file=stream)
    return 0
