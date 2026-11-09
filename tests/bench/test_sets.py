"""The benchmark, its task sets, pins and the release check (R-83, R-108, R-111). No real data."""
import importlib
import json
from pathlib import Path

import pytest
import yaml

from medomni.bench import task
from medomni.bench.build import sets
from medomni.core.contracts import TaskSet, load, load_data

REPO = Path(__file__).resolve().parents[2]
BENCH = REPO / "bench/benchmarks/medomni-bench"


def set_of(pairs, arms=("encoders",)):
    return load_data({"name": "x", "arms": list(arms), "tasks": [{"task": p, "version": v} for p, v in pairs]}, TaskSet, "x")


def test_every_shipped_set_loads_and_its_pins_match_the_cohorts():
    for name in ("v1", "modality-ladder", "smoke-dummy", "vitaldb"):
        s, _ = sets.load_set(f"medomni-bench/{name}")
        def text(pair):
            package, tid, co = sets.package_of(pair)
            return (package / "tasks" / tid / "cohorts" / f"{co}.yaml").read_text()
        assert sets.pin_problems(s, text) == [], name
    assert len(load(BENCH / "sets/v1.yaml", TaskSet).tasks) == 30


def test_an_unknown_set_is_refused():
    with pytest.raises(sets.BuildError):
        sets.load_set("medomni-bench/nope")
    with pytest.raises(sets.BuildError):
        sets.load_set("nope")


def test_the_set_hash_covers_only_the_pairs_and_their_n():
    a, b = set_of([("a_b@n20", 1), ("c_d@n20", 1)]), set_of([("c_d@n20", 1), ("a_b@n20", 1)], arms=("no-perception",))
    assert sets.task_set_hash(a) == sets.task_set_hash(b)
    assert sets.task_set_hash(a) != sets.task_set_hash(set_of([("a_b@n20", 2), ("c_d@n20", 1)]))


@pytest.fixture
def package(tmp_path):
    p = tmp_path / "bench/datasets/d"
    t = p / "tasks/d_t"
    (t / "cohorts").mkdir(parents=True)
    (t / "cohorts/n20.yaml").write_text("version: '1.0'\nanchor: {event: A}\ndraw: {n: 20, seed: 7}\n")
    (t / "template.yaml").write_text("targets:\n- {name: y, label: 'd:l', metric: auc}\nagent: {statement: old words}\n")
    (p / "labels.yaml").write_text("l: {exists: X, from: any, to: any, question: old}\n")
    (p / "dataset.yaml").write_text("description: {version: '1'}\n")
    return p


def _check(package, version=1):
    old = {}
    for rel in ("tasks/d_t/cohorts/n20.yaml", "tasks/d_t/template.yaml", "labels.yaml", "dataset.yaml"):
        old[package / rel] = (package / rel).read_text()
    return old


def _problems(package, old, version=1):
    return sets.release_problems(set_of([("d_t@n20", version)]), "b/s", lambda p: (package, "d_t", "n20"), old.get)


def test_a_label_change_fails_until_n_rises_and_wording_passes(package):
    old = _check(package)
    assert _problems(package, old) == []
    (package / "labels.yaml").write_text("l: {exists: Y, from: any, to: any, question: old}\n")
    assert _problems(package, old)
    assert _problems(package, old, version=2) == []
    (package / "labels.yaml").write_text("l: {exists: X, from: any, to: any, question: new words}\n")
    (package / "tasks/d_t/template.yaml").write_text("targets:\n- {name: y, label: 'd:l', metric: auc}\nagent: {statement: new}\n")
    assert _problems(package, old) == []


def test_a_new_pair_compares_with_nothing(package):
    assert _problems(package, {}) == []


def test_a_scoring_change_fails(package):
    old = _check(package)
    (package / "tasks/d_t/template.yaml").write_text("targets:\n- {name: y, label: 'd:l', metric: qwk}\nagent: {statement: old words}\n")
    assert _problems(package, old)


def test_a_second_benchmark_with_its_own_v1_loads_beside_it(tmp_path, monkeypatch):
    from medomni.core import plugins

    other = tmp_path / "bench/benchmarks/other"
    (other / "sets").mkdir(parents=True)
    (other / "benchmark.yaml").write_text("name: other\nversion: '1'\nowner: x\nlicense: MIT\naccepts: [agent]\n")
    (other / "sets/v1.yaml").write_text("name: v1\narms: [encoders]\ntasks: [{task: aireadi_x@n20, version: 1}]\n")
    real = plugins.roots
    monkeypatch.setattr(plugins, "roots", lambda repo: ([*real(repo)[0], ("other", tmp_path)], []))
    assert sets.load_set("other/v1")[0].tasks[0].task == "aireadi_x@n20"
    assert len(sets.load_set("medomni-bench/v1")[0].tasks) == 30


def test_task_check_needs_something_named(capsys):
    assert task.check(None, None, False) == 2


def test_task_new_writes_files_that_parse(tmp_path, monkeypatch):
    import medomni.core.loading as loading

    p = tmp_path / "bench/datasets/d"
    p.mkdir(parents=True)
    monkeypatch.setattr(loading, "find_package", lambda name: p)
    assert task.new("my-task", "d") == 0
    assert task.new("my-task", "d") == 1
    assert yaml.safe_load((p / "tasks/d_my-task/template.yaml").read_text())["template_id"] == "d_my-task"
