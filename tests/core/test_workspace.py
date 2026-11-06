"""The workspace config (part 7): found under MEDOMNI_HOME or ~/.medomni; absolute paths; errors name the field."""
import pytest
import yaml

from medomni.core import workspace
from medomni.core.contracts import ContractError

from .contract_examples import EXAMPLES

FULL = dict(EXAMPLES["workspace-config"][0], hf_cache="/srv/ws/hf", scratch="/srv/ws/tmp")


def _write(d, data):
    d.mkdir(parents=True, exist_ok=True)
    (d / "workspace.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def test_full_config_loads(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDOMNI_HOME", str(tmp_path / "ws"))
    _write(tmp_path / "ws", FULL)
    cfg = workspace.load()
    assert cfg.cache == "/srv/ws/cache" and cfg.hf_cache == "/srv/ws/hf"
    assert str(workspace.dataset_path(cfg, "dummy")) == "/srv/data/dummy"
    with pytest.raises(workspace.WorkspaceError, match="datasets.mimic-iv.path"):
        workspace.dataset_path(cfg, "mimic-iv")


@pytest.mark.parametrize("change, field", [
    ({"cache": None}, "cache"),
    ({"tasks": "relative/tasks"}, "tasks"),
    ({"datasets": {"dummy": {"path": "data/dummy"}}}, "datasets.dummy.path"),
    ({"colour": "blue"}, "colour"),
])
def test_refused_configs_name_the_field(tmp_path, monkeypatch, change, field):
    data = dict(FULL)
    for k, v in change.items():
        data.pop(k) if v is None else data.__setitem__(k, v)
    monkeypatch.setenv("MEDOMNI_HOME", str(tmp_path / "ws"))
    _write(tmp_path / "ws", data)
    with pytest.raises(ContractError) as e:
        workspace.load()
    assert field in str(e.value)


def test_medomni_home_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    _write(tmp_path / "home/.medomni", dict(FULL, cache="/from/home"))
    _write(tmp_path / "ws", dict(FULL, cache="/from/env"))
    monkeypatch.setenv("MEDOMNI_HOME", str(tmp_path / "ws"))
    assert workspace.load().cache == "/from/env"
    monkeypatch.delenv("MEDOMNI_HOME")
    assert workspace.load().cache == "/from/home"


def test_no_config_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("MEDOMNI_HOME")
    with pytest.raises(workspace.WorkspaceError, match="no workspace config .*set MEDOMNI_HOME"):
        workspace.load()
    monkeypatch.setenv("MEDOMNI_HOME", str(tmp_path / "ws"))
    with pytest.raises(workspace.WorkspaceError, match="no workspace config"):
        workspace.load()


def test_relative_medomni_home_is_refused(monkeypatch):
    monkeypatch.setenv("MEDOMNI_HOME", "ws")
    with pytest.raises(workspace.WorkspaceError, match="absolute"):
        workspace.home()
