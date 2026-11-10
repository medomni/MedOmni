"""The v1 builder's checks on task sets (R-108): each pin's N against its cohort file, and the release check. Reading
sets and `task_set_hash` are Core's (`medomni.core.tasks.sets`). The release check compares config files only, never data.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import yaml

from medomni.core.contracts import TaskSet

from .pool import BuildError, parse


from medomni.core.tasks.sets import all_sets, benchmark_folders, load_set, task_set_hash  # noqa: F401  (Core, R-143 b)


def pin_problems(task_set: TaskSet, read_cohort) -> list[str]:
    """Each entry's N equals its cohort file's major version. `read_cohort(pair)` gives the cohort's text, or None."""
    out = []
    for e in task_set.tasks:
        if e.version == 0:  # imported v0.2 sets
            continue
        text = read_cohort(e.task)
        if text is None:
            out.append(f"{e.task}: no cohort file")
        elif int(str(yaml.safe_load(text)["version"]).split(".")[0]) != e.version:
            out.append(f"{e.task}: pinned at version {e.version}, but its cohort is at {yaml.safe_load(text)['version']}")
    return out


# ---- the release check
def comparable(cohort: str, template: str, labels: str, dataset: str) -> dict:
    """What decides whether two results compare: cohort, targets and their scoring, the labels they name, and the dataset
    release. Wording (the agent block, a label's `question`) does not."""
    co = yaml.safe_load(cohort)
    co.pop("version", None)
    tpl, lib = yaml.safe_load(template), yaml.safe_load(labels)
    targets = [{k: t[k] for k in ("name", "label", "metric")} for t in tpl["targets"]]
    named = {}
    for t in targets:
        rule = dict(lib.get(t["label"].split(":", 1)[1]) or {})
        rule.pop("question", None)
        named[t["label"]] = rule
    return {"cohort": co, "targets": targets, "labels": named, "release": yaml.safe_load(dataset)["description"]["version"]}


def files_of(package: Path, template_id: str, cohort: str) -> dict[str, Path]:
    t = package / "tasks" / template_id
    return {"cohort": t / "cohorts" / f"{cohort}.yaml", "template": t / "template.yaml", "labels": package / "labels.yaml",
            "dataset": package / "dataset.yaml"}


def release_problems(task_set: TaskSet, set_name: str, package_of, read_old) -> list[str]:
    """A pinned pair whose comparable config differs from the last release, with no rise in N, fails.

    `package_of(pair)` gives (package folder, template id, cohort); `read_old(path)` gives a file's text at the last release,
    or None when it did not exist there (a new pair compares with nothing)."""
    out = []
    for e in task_set.tasks:
        if e.version == 0:
            continue
        package, template_id, cohort = package_of(e.task)
        files = files_of(package, template_id, cohort)
        old = {k: read_old(p) for k, p in files.items()}
        if any(v is None for v in old.values()):
            continue
        new = {k: p.read_text(encoding="utf-8") for k, p in files.items()}
        was = int(str(yaml.safe_load(old["cohort"])["version"]).split(".")[0])
        if e.version <= was and comparable(**old) != comparable(**new):
            out.append(f"{set_name}: {e.task} changed in cohort, labels, targets, scoring or dataset release, and its N did not rise")
    return out


def last_release(repo: Path) -> str | None:
    tags = subprocess.run(["git", "tag", "--list", "--sort=-v:refname", "v[0-9]*"], cwd=repo, capture_output=True, text=True).stdout.split()
    return tags[0] if tags else None


def git_reader(repo: Path, tag: str | None):
    def read(path: Path) -> str | None:
        if tag is None:
            return None
        rel = Path(path).relative_to(repo).as_posix()
        r = subprocess.run(["git", "show", f"{tag}:{rel}"], cwd=repo, capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    return read


def package_of(pair: str):
    from medomni.core.loading import find_package

    template_id, _, cohort = parse(pair)
    return find_package(template_id.split("_", 1)[0]), template_id, cohort
