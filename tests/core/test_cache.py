"""The cache (Cache page, R-155): keys from a step's arguments, the `folder` and `none` backends, a plug-in backend,
and the commands. Nothing checks what a result holds, so there is no `verify`."""
import json
import sys

import pytest
import yaml

from medomni.core import cache as c
from medomni.core import plugins
from medomni.core.cache import commands
from medomni.core.cache.folder import FolderCache
from medomni.core.cache.none import NoCache
from medomni.core.cli import main
from medomni.core.contracts import WorkspaceConfig, load_data

from .test_plugins import make_dist


def _ws(home, cache):
    cfg = {"cache": cache, "tasks": str(home / "tasks"), "runs": str(home / "runs"), "keys_file": str(home / "keys"),
           "results": str(home / "results.jsonl")}
    (home / "workspace.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return load_data(cfg, WorkspaceConfig, "workspace.yaml")


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """A workspace on the folder backend; MEDOMNI_HOME names it."""
    home = tmp_path / "ws"
    home.mkdir()
    _ws(home, str(home / "cache"))
    monkeypatch.setenv("MEDOMNI_HOME", str(home))
    monkeypatch.setattr(c, "CORE_STEPS", {"events": "1"})
    return FolderCache(home / "cache")


@pytest.fixture
def raw(tmp_path):
    p = tmp_path / "raw/patients.csv"
    p.parent.mkdir()
    p.write_text("subject_id,age\nDUMMY-1,40\n")
    return p


def _make(text="a,b\n1,2\n", calls=None):
    def make(d):
        if calls is not None:
            calls.append(d)
        (d / "events.csv").write_text(text)
        (d / "parts").mkdir()
        (d / "parts/0.txt").write_text("x")
        return {"events": 1}
    return make


def _run(cache, raw, version="1", params=None, text="a,b\n1,2\n", calls=None):
    return cache.run("dummy", "events", version, params or {"tables": ["patients"]},
                     [c.file_input(raw, "patients.csv")], _make(text, calls))


# ---------------------------------------------------------------- keys


def test_key_changes_with_inputs_params_and_version(ws, raw):
    k = _run(ws, raw)[0].key
    assert _run(ws, raw)[0].key == k  # same arguments, same key
    assert _run(ws, raw, version="2")[0].key != k
    assert _run(ws, raw, params={"tables": ["admissions"]})[0].key != k
    raw.write_text(raw.read_text().replace("40", "41"))
    assert _run(ws, raw)[0].key != k


def test_key_is_canonical():
    a = c.key("events", "1", {"b": 1, "a": [1, 2]}, [("x", "1" * 64), ("y", "2" * 64)])
    b = c.key("events", "1", {"a": [1, 2], "b": 1}, [("y", "2" * 64), ("x", "1" * 64)])
    assert a == b and len(a) == 64


# ---------------------------------------------------------------- the folder backend


def test_folder_writes_a_result_with_no_content_hash(ws, raw):
    r, created = _run(ws, raw)
    assert created and r.path == ws.folder("dummy", "events", r.key) and r.rows == {"events": 1}
    meta = json.loads((r.path / "CACHE.json").read_text())
    assert "content_hash" not in meta and meta["inputs"][0]["name"] == "patients.csv"
    assert not any(p.is_symlink() for p in r.path.rglob("*"))
    assert not list(ws.root.glob("*/*/*.tmp-*"))


def test_folder_reads_a_result_written_before_r155(ws, raw):
    r, _ = _run(ws, raw)
    meta = json.loads((r.path / "CACHE.json").read_text())
    (r.path / "CACHE.json").write_text(json.dumps({**meta, "content_hash": "0" * 64}))
    again, created = _run(ws, raw)
    assert not created and again == r


def test_an_existing_key_is_left_alone(ws, raw):
    r, _ = _run(ws, raw)
    before = (r.path / "CACHE.json").read_bytes()
    calls = []
    again, created = _run(ws, raw, text="something else\n", calls=calls)
    assert not created and again.path == r.path and calls == []
    assert (r.path / "CACHE.json").read_bytes() == before and (r.path / "events.csv").read_text() == "a,b\n1,2\n"


def test_a_failed_step_leaves_nothing(ws, raw):
    def fail(d):
        (d / "half.csv").write_text("a")
        raise RuntimeError("step failed")
    with pytest.raises(RuntimeError):
        ws.run("dummy", "events", "1", {}, [c.file_input(raw, "patients.csv")], fail)
    assert not list(ws.folders())


@pytest.mark.parametrize("backend", ["folder", "none"])
def test_a_link_in_a_result_is_refused(tmp_path, raw, backend):
    cache = FolderCache(tmp_path / "cache") if backend == "folder" else NoCache(tmp_path / "tmp")

    def link(d):
        (d / "x").symlink_to(raw)
        return {}
    with pytest.raises(c.CacheError, match="a link"):
        cache.run("dummy", "events", "1", {}, [], link)
    assert not list((tmp_path / "cache").glob("*/*/*")) if backend == "folder" else True


def test_row_counts_must_be_counts(tmp_path):
    with pytest.raises(c.CacheError, match="row counts"):
        FolderCache(tmp_path / "cache").run("dummy", "events", "1", {}, [], lambda d: {"events": "many"})


# ---------------------------------------------------------------- the none backend


def test_none_keeps_nothing_between_processes(tmp_path, raw):
    cache = NoCache(tmp_path / "tmp")
    calls = []
    r, created = _run(cache, raw, calls=calls)
    assert created and (r.path / "events.csv").read_text() == "a,b\n1,2\n"
    again, created = _run(cache, raw, calls=calls)
    assert not created and again.path == r.path and len(calls) == 1  # once per process
    other, created = _run(NoCache(tmp_path / "tmp"), raw)  # another process's cache starts empty
    assert created and other.path != r.path and other.key == r.key
    cache.close()
    assert not r.path.exists() and other.path.exists()


# ---------------------------------------------------------------- choosing a backend


def test_a_path_is_the_folder_backend(tmp_path):
    ws = _ws(tmp_path, str(tmp_path / "cache"))
    backend = c.of(ws)
    assert isinstance(backend, FolderCache) and backend.root == tmp_path / "cache"
    assert c.open_cache(backend.spec).root == backend.root  # what a worker process opens


def test_a_named_backend(tmp_path):
    assert isinstance(c.of(_ws(tmp_path, {"backend": "none"})), NoCache)
    assert isinstance(c.of(_ws(tmp_path, {"backend": "folder", "path": str(tmp_path / "c")})), FolderCache)


def test_backend_errors(tmp_path):
    with pytest.raises(c.CacheError, match="no cache backend 'nope'; known: folder, none"):
        c.of(_ws(tmp_path, {"backend": "nope"}))
    with pytest.raises(c.CacheError, match="needs a path"):
        c.of(_ws(tmp_path, {"backend": "folder"}))
    with pytest.raises(Exception, match="absolute"):
        _ws(tmp_path, "relative/cache")


COUNTING = '''
from medomni.core.cache.none import NoCache

RUNS = []


class Counting(NoCache):
    name = "counting"

    def __init__(self, path=None, label="x"):
        super().__init__(path)
        self.label = label

    def run(self, *args):
        RUNS.append((self.label, args[1]))
        return super().run(*args)
'''


def test_a_backend_from_a_plug_in_package(tmp_path, monkeypatch, raw):
    """A plug-in package adds a backend in `medomni.caches`; Core does not change (R-155)."""
    site = tmp_path / "site"
    site.mkdir()
    monkeypatch.syspath_prepend(str(site))
    make_dist(site, "medomni-counting", "fake_counting", {plugins.CACHES: {"counting": "fake_counting:Counting"}})
    (site / "fake_counting" / "__init__.py").write_text(COUNTING)
    try:
        backend = c.of(_ws(tmp_path, {"backend": "counting", "options": {"label": "mine"}}))
        r, created = _run(backend, raw)
        assert created and (r.path / "events.csv").is_file()
        assert sys.modules["fake_counting"].RUNS == [("mine", "events")]
    finally:
        for m in [m for m in sys.modules if m.startswith("fake_")]:
            del sys.modules[m]


# ---------------------------------------------------------------- commands


def test_gc_removes_unused_results_and_tmp_folders(ws, raw, capsys):
    used, _ = _run(ws, raw)
    old, _ = _run(ws, raw, version="0")  # no current step has version 0
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
    assert "no results" in capsys.readouterr().out  # an empty workspace
    _run(ws, raw)
    _run(ws, raw, version="0")
    assert main(["cache", "status"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("cache: folder at ")
    line = next(l for l in out.splitlines() if "events" in l)
    assert line.split()[:3] == ["dummy", "events", "2"] and line.split()[-1] == "1"


def test_a_backend_without_status_or_gc_says_so(tmp_path, monkeypatch, capsys):
    home = tmp_path / "ws"
    home.mkdir()
    _ws(home, {"backend": "none"})
    monkeypatch.setenv("MEDOMNI_HOME", str(home))
    assert main(["cache", "status"]) == 2
    assert "the 'none' cache backend has no `status`" in capsys.readouterr().err
    assert main(["cache", "gc"]) == 2


def test_there_is_no_verify(ws, capsys):
    """Nothing checks what the cache holds (R-111, R-155)."""
    assert main(["cache", "verify"]) == 2
    assert "invalid choice: 'verify'" in capsys.readouterr().err


def test_commands_need_a_workspace(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEDOMNI_HOME", str(tmp_path / "none"))
    assert commands.main(["status"]) == 2
    assert "no workspace config" in capsys.readouterr().err
