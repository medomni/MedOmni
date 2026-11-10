"""The builder looks a dataset's events entry up once per process: its cache key covers every data file."""
from pathlib import Path
from types import SimpleNamespace

from medomni.studio import build


def test_events_entry_is_looked_up_once(tmp_path, monkeypatch):
    calls = []

    def fake_load(package, raw, cache):
        calls.append(package)
        return SimpleNamespace(path=tmp_path / "entry"), False

    monkeypatch.setattr(build, "load_dataset", fake_load)
    monkeypatch.setattr(build, "_EVENTS", {})
    monkeypatch.setattr(build.workspace, "dataset_path", lambda ws, d: tmp_path / d)
    cache = SimpleNamespace(root=tmp_path / "cache")
    pair = SimpleNamespace(package=Path("pkg-a"), dataset="a")
    for _ in range(3):
        assert build._dataset_events(pair, None, cache) == (tmp_path / "a", tmp_path / "entry/events.parquet")
    build._dataset_events(SimpleNamespace(package=Path("pkg-b"), dataset="b"), None, cache)
    assert calls == [Path("pkg-a"), Path("pkg-b")]
