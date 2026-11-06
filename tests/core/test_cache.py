"""The cache (part 7): keys, immutable entries, verify, gc, and the four commands."""
import json

import pytest
import yaml

from medomni.core import cache as c
from medomni.core.cache import commands
from medomni.core.cli import main
from medomni.core.contracts import CacheEntry, load

from .contract_examples import EXAMPLES


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """An empty workspace whose config points at tmp folders; MEDOMNI_HOME names it."""
    home = tmp_path / "ws"
    home.mkdir()
    cfg = {k: str(home / k) for k in ("cache", "tasks", "runs", "keys_file")} | {"results": str(home / "results.jsonl")}
    (home / "workspace.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    monkeypatch.setenv("MEDOMNI_HOME", str(home))
    monkeypatch.setattr(c, "CORE_STEPS", {"events": "1"})
    return c.Cache(home / "cache")


@pytest.fixture
def raw(tmp_path):
    p = tmp_path / "raw/patients.csv"
    p.parent.mkdir()
    p.write_text("subject_id,age\nDUMMY-1,40\n")
    return p


def _write(text="a,b\n1,2\n"):
    def write(d):
        (d / "events.csv").write_text(text)
        (d / "parts").mkdir()
        (d / "parts/0.txt").write_text("x")
        return {"events": 1}
    return write


def _build(cache, raw, version="1", params=None, text="a,b\n1,2\n"):
    return cache.create("dummy", "events", version, params or {"tables": ["patients"]},
                        [c.file_input(raw, "patients.csv")], _write(text))


def test_build_writes_a_valid_entry(ws, raw):
    e, created = _build(ws, raw)
    assert created and e.path == ws.folder("dummy", "events", e.meta.key)
    meta = load(e.path / "CACHE.json", CacheEntry)
    assert meta.rows == {"events": 1} and meta.inputs[0].name == "patients.csv"
    assert c.verify(e) == []
    assert not any(p.is_symlink() for p in e.path.rglob("*"))
    assert not list(ws.root.glob("*/*/*.tmp-*"))


def test_key_changes_with_inputs_params_and_version(ws, raw):
    k = _build(ws, raw)[0].meta.key
    assert _build(ws, raw)[0].meta.key == k  # same inputs, same key
    assert _build(ws, raw, version="2")[0].meta.key != k
    assert _build(ws, raw, params={"tables": ["admissions"]})[0].meta.key != k
    raw.write_text(raw.read_text().replace("40", "41"))
    assert _build(ws, raw)[0].meta.key != k


def test_key_is_canonical():
    a = c.key("events", "1", {"b": 1, "a": [1, 2]}, [("x", "1" * 64), ("y", "2" * 64)])
    b = c.key("events", "1", {"a": [1, 2], "b": 1}, [("y", "2" * 64), ("x", "1" * 64)])
    assert a == b and len(a) == 64


def test_existing_key_is_left_alone(ws, raw):
    e, _ = _build(ws, raw)
    before = (e.path / "CACHE.json").read_bytes()
    again, created = _build(ws, raw, text="something else\n")
    assert not created and again.path == e.path
    assert (e.path / "CACHE.json").read_bytes() == before and (e.path / "events.csv").read_text() == "a,b\n1,2\n"


def test_a_failed_step_leaves_nothing(ws, raw):
    def fail(d):
        (d / "half.csv").write_text("a")
        raise RuntimeError("step failed")
    with pytest.raises(RuntimeError):
        ws.create("dummy", "events", "1", {}, [c.file_input(raw, "patients.csv")], fail)
    assert not list(ws.folders())


def test_a_link_in_an_entry_is_refused(ws, raw, tmp_path):
    def link(d):
        (d / "x").symlink_to(raw)
        return {}
    with pytest.raises(Exception, match="a link"):
        ws.create("dummy", "events", "1", {}, [], link)
    assert not list(ws.folders())


def test_verify_catches_an_edited_file(ws, raw, capsys):
    e, _ = _build(ws, raw)
    assert main(["cache", "verify"]) == 0
    (e.path / "parts/0.txt").write_text("y")
    assert c.verify(e) and "content hash" in c.verify(e)[0]
    assert main(["cache", "verify"]) == 1
    assert f"FAIL  dummy/events/{e.meta.key}" in capsys.readouterr().out


def test_verify_catches_an_edited_cache_json(ws, raw):
    e, _ = _build(ws, raw)
    meta = json.loads((e.path / "CACHE.json").read_text())
    meta["params"] = {"tables": ["other"]}
    (e.path / "CACHE.json").write_text(json.dumps(meta))
    assert any("do not give its key" in p for p in c.verify(ws.read(e.path)))


def test_verify_set_names_the_differing_entry(ws, raw, tmp_path, capsys):
    good, _ = _build(ws, raw)
    other, _ = _build(ws, raw, version="2")
    s = EXAMPLES["task-set"][0]
    entry = dict(s["tasks"][0], cache=[{"key": good.meta.key, "content_hash": good.meta.content_hash},
                                       {"key": other.meta.key, "content_hash": "f" * 64}])
    p = tmp_path / "smoke-dummy.yaml"
    p.write_text(yaml.safe_dump(dict(s, tasks=[entry])))
    assert main(["cache", "verify", "--set", str(p)]) == 1
    out = capsys.readouterr().out
    assert f"DIFFERS  dummy_aki@n20: dummy/events/{other.meta.key}" in out
    assert good.meta.key not in out.split("DIFFERS")[1] and "1/2 published entries match" in out


def test_gc_removes_unused_entries_and_tmp_folders(ws, raw, capsys):
    used, _ = _build(ws, raw)
    old, _ = _build(ws, raw, version="0")  # no current step has version 0
    tmp = used.path.parent / f"{'0' * 64}.tmp-12345"
    tmp.mkdir()
    (tmp / "half").write_text("x")
    assert main(["cache", "gc", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "would remove" in out and "2 folder(s) to remove" in out
    assert old.path.exists() and tmp.exists()
    assert main(["cache", "gc"]) == 0
    assert not old.path.exists() and not tmp.exists() and used.path.exists()


def test_status(ws, raw, capsys):
    assert main(["cache", "status"]) == 0
    assert "no entries" in capsys.readouterr().out  # an empty workspace
    _build(ws, raw)
    _build(ws, raw, version="0")
    assert main(["cache", "status"]) == 0
    line = next(l for l in capsys.readouterr().out.splitlines() if "events" in l)
    assert line.split()[:3] == ["dummy", "events", "2"] and line.split()[-1] == "1"


def test_commands_need_a_workspace(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEDOMNI_HOME", str(tmp_path / "none"))
    assert commands.main(["status"]) == 2
    assert "no workspace config" in capsys.readouterr().err
