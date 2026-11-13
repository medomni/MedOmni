"""Core's checks over built output alone (R-143 a): any builder's tasks, before every run."""
import json

import yaml

from medomni.core.tasks import asset, checks, layout


def _atom(root, compose=None, refs=None, mapping=None, prediction_time="2150-01-01 00:00:00"):
    a = root / "atom"
    (a / "environment").mkdir(parents=True)
    (a / "data").mkdir()
    (a / "tests").mkdir()
    (a / "environment/docker-compose.yaml").write_text(yaml.safe_dump(compose or {
        "services": {"main": {"networks": ["n"]}, "bootstrap": {"networks": ["n"]}}, "networks": {"n": {"internal": True}}}))
    (a / "environment/Dockerfile").write_text(asset("environment", "Dockerfile"))
    (a / "task.toml").write_text(f'version = "1.0"\n\n[atom]\nprediction_time = "{prediction_time}"\n')
    (a / "instruction.md").write_text("# a task\n")
    (a / "tests/format_check.py").write_text(asset("formatcheck", "format_check.py"))
    (a / "tests/test.sh").write_text(asset("formatcheck", "test.sh"))
    (a / "tests/expected.json").write_text(json.dumps({"targets": ["t"]}))
    if refs:
        (a / "data/references.jsonl").write_text("".join(json.dumps(r) + "\n" for r in refs))
    if mapping:
        (a / "environment/refs.map.json").write_text(json.dumps(mapping))
    return a


def test_a_whole_atom_passes(tmp_path):
    assert checks.atom_checks(_atom(tmp_path)) == []


def test_closed_network(tmp_path):
    assert checks.network(_atom(tmp_path)) == []
    a = _atom(tmp_path / "b", {"services": {"main": {"networks": ["n"]}}, "networks": {"n": {}}})
    assert checks.network(a)
    a = _atom(tmp_path / "c", {"services": {"main": {"networks": ["n"]}, "x": {}}, "networks": {"n": {"internal": True}}})
    assert checks.network(a)


def test_nothing_after_the_prediction_time(tmp_path):
    """Read from the atom alone: each reference's t_start against task.toml's prediction time."""
    late = _atom(tmp_path, refs=[{"path": "refs/f/x.jpg", "t_start": "2150-01-02 00:00:00"}])
    assert checks.image_times(late)
    ok = _atom(tmp_path / "b", refs=[{"path": "refs/f/x.jpg", "t_start": "2150-01-01 00:00:00"}])
    assert checks.image_times(ok) == []
    absolute = _atom(tmp_path / "c", refs=[{"path": "/raw/x.jpg"}])
    assert checks.image_times(absolute)


def test_complete_recordings(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "r.hea").write_text("r 1 500 100\nr.dat 16 200 12 0 0 0 0 I\n")
    (raw / "r.dat").write_bytes(b"\0\0")
    whole = _atom(tmp_path / "a", mapping={"refs/f/r.hea": str(raw / "r.hea"), "refs/f/r.dat": str(raw / "r.dat")})
    part = _atom(tmp_path / "b", mapping={"refs/f/r.hea": str(raw / "r.hea")})
    assert checks.recordings(whole) == [] and checks.recordings(part)


def test_no_gold_in_an_atom(tmp_path):
    a = _atom(tmp_path)
    (a / "data/answers.csv").write_text("subject_id,target,value,metric\n")
    assert checks.no_gold(a)
    b = _atom(tmp_path / "b")
    (b / "tests/expected.json").write_text(json.dumps({"targets": ["t"], "values": {"t": 1}}))
    assert checks.no_gold(b)


def test_the_format_check_runs(tmp_path):
    a = _atom(tmp_path)
    assert checks.format_check(a) == []
    (a / "tests/format_check.py").write_text("print('{}')\n")
    assert checks.format_check(a)


def test_a_task_needs_its_contract_files(tmp_path):
    tree = tmp_path / "atomtasks"
    d = layout.content_dir(tree, "x_y@n4")
    d.mkdir(parents=True)
    assert len(checks.contract_files(tree, "x_y@n4")[0]) == 3
    (d / "content.json").write_text(json.dumps({"version": "1.0", "targets": [{"name": "t", "metric": "auc"}],
                                                "atoms": [{"atom": "a", "subject": "1"}]}))
    (d / "manifest.json").write_text(json.dumps({"config_hash": {"encoders": "cfg1:" + "0" * 64}, "builder": "b/1"}))
    (d / "answers.csv").write_text("subject_id,target,value,metric\n")
    problems, content = checks.contract_files(tree, "x_y@n4")
    assert problems == [] and content.atoms[0].atom == "a"
    assert layout.variants(tree, "x_y@n4", "encoders") == [None]
    assert any("not built under" in p for p in checks.task_checks(tree, "x_y@n4", ["encoders"]))
