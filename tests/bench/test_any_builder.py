"""R-142, R-143: Bench runs and scores what any builder writes in Core's built-task contract, with Studio absent.

The outside builder below is test code: it subclasses Core's `TaskBuilder`, imports nothing from Studio, and writes a
set of tiny atoms with Core's shared atom files. Nothing in Core, Bench or Studio names it.
"""
import csv
import importlib.abc
import json
import sys
from pathlib import Path

import pytest
import yaml

from medomni.bench import runs as runs_mod
from medomni.core import hashing, plugins, workspace
from medomni.core.builders import TaskBuilder, builder
from medomni.core.contracts import RunRecord, TaskSet, load_data, load_lines
from medomni.core.tasks import asset, layout

TASK, SET = "outside_risk@x", "outside-bench/s"


class OutsideBuilder(TaskBuilder):
    name, version = "outside", "1"

    def config_files(self, task, arm, variant):
        return {"outside-config": f"{task}|{arm}|{variant}".encode()}

    def build(self, tasks, arms, workspace_):
        tree = layout.tree(workspace_)
        out = []
        for task in tasks:
            d = layout.content_dir(tree, task)
            d.mkdir(parents=True, exist_ok=True)
            atoms = [{"atom": f"outside__{i}", "subject": str(i)} for i in range(6)]
            (d / "content.json").write_text(json.dumps({"version": "1.0", "targets": [{"name": "risk", "metric": "auc"}],
                                                        "atoms": atoms}))
            with open(d / "answers.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["subject_id", "target", "value", "metric"])
                w.writerows((a["subject"], "risk", i % 2, "auc") for i, a in enumerate(atoms))
            hashes = {a: hashing.config_hash(self.config_files(task, a, None), dataset_release="1", medomni_release="x")
                      for a in arms}
            (d / "manifest.json").write_text(json.dumps({"config_hash": hashes, "builder": self.label}))
            for arm in arms:
                for a in atoms:
                    _atom(layout.atom_dir(tree, arm, None, a["atom"]))
            out.append(d)
        return out


def _atom(a: Path) -> None:
    for sub in ("environment", "data", "tests"):
        (a / sub).mkdir(parents=True, exist_ok=True)
    (a / "task.toml").write_text('version = "1.0"\n\n[atom]\nprediction_time = ""\n')
    (a / "instruction.md").write_text("# Predict the risk.\n")
    (a / "environment/Dockerfile").write_text(asset("environment", "Dockerfile"))
    (a / "environment/docker-compose.yaml").write_text(yaml.safe_dump(
        {"services": {"main": {"networks": ["n"]}}, "networks": {"n": {"internal": True}}}))
    (a / "tests/format_check.py").write_text(asset("formatcheck", "format_check.py"))
    (a / "tests/test.sh").write_text(asset("formatcheck", "test.sh"))
    (a / "tests/expected.json").write_text(json.dumps({"targets": ["risk"]}))


@pytest.fixture
def outside(tmp_path, monkeypatch):
    cfg = tmp_path / "workspace.yaml"
    cfg.write_text(f"datasets: {{}}\ncache: {tmp_path}/cache\ntasks: {tmp_path}/tasks\nruns: {tmp_path}/runs\n"
                   f"results: {tmp_path}/results.jsonl\nhf_cache: {tmp_path}/hf\n")
    ws = workspace.load(cfg)
    task_set = load_data({"name": "s", "builder": "outside", "arms": ["encoders"], "tasks": [{"task": TASK, "version": 1}]},
                         TaskSet, "set")
    real = plugins.resolve

    def resolve(group):
        out = real(group)
        if group == plugins.BUILDERS:
            piece = type("P", (), {"load": staticmethod(OutsideBuilder)})()
            return type(out)(**{**out.__dict__, "pieces": {**out.pieces, "outside": piece}})
        return out

    monkeypatch.setattr(plugins, "resolve", resolve)
    monkeypatch.setattr(runs_mod, "load_set", lambda name: (task_set, None))
    return ws, task_set


def test_a_set_from_an_outside_builder_runs_and_scores(outside):
    ws, task_set = outside
    builder(task_set.builder).build([TASK], list(task_set.arms), ws)  # what `studio task build --set` does for this set
    job = runs_mod.run(SET, "terminus-2-replay", ws=ws)[0]
    assert len(load_lines(job / "runs.jsonl", RunRecord)) == 6
    assert runs_mod.score(SET, ws=ws) == 0
    rows = [json.loads(x) for x in Path(ws.results).read_text().splitlines()]
    assert {r["target"] for r in rows} == {"risk"} and rows[0]["value"] == 0.5  # the replay's constant answer


def test_a_broken_built_task_runs_nothing(outside):
    ws, task_set = outside
    builder(task_set.builder).build([TASK], list(task_set.arms), ws)
    (layout.atom_dir(layout.tree(ws), "encoders", None, "outside__0") / "data/answers.csv").write_text("leak\n")
    with pytest.raises(runs_mod.RunError, match="no gold"):
        runs_mod.run(SET, "terminus-2-replay", ws=ws)
    assert not list(Path(ws.runs).glob("*")) if Path(ws.runs).exists() else True


class _NoStudio(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "medomni.studio" or name.startswith("medomni.studio."):
            raise ImportError(f"{name}: Studio is blocked in this test")
        return None


def test_bench_runs_and_scores_with_studio_blocked(outside, monkeypatch):
    """Check 8, new form (R-143): built tasks in hand, Bench runs and scores without Studio."""
    ws, task_set = outside
    OutsideBuilder().build([TASK], list(task_set.arms), ws)
    for name in [m for m in sys.modules if m == "medomni.studio" or m.startswith("medomni.studio.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "meta_path", [_NoStudio(), *sys.meta_path])
    with pytest.raises(ImportError):
        import medomni.studio.build  # noqa: F401
    job = runs_mod.run(SET, "terminus-2-replay", ws=ws)[0]
    assert len(load_lines(job / "runs.jsonl", RunRecord)) == 6
    assert runs_mod.score(SET, ws=ws) == 0
