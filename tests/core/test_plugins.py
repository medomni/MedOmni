"""Plug-in loading: lazy listing, import errors, name clashes (R-65)."""
import sys
from pathlib import Path

import pytest

from medomni.core import plugins
from medomni.core.cli import main


def make_dist(root: Path, dist: str, module: str, entry_points: dict[str, dict[str, str]]) -> None:
    """Write an installed-looking distribution: a module and a .dist-info folder with entry_points.txt."""
    pkg = root / module
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "def group(argv):\n    print('ran', __name__)\n    return 0\n\nOBJ = object()\n"
    )
    (pkg / "lazy.py").write_text("OBJ = object()\n")
    info = root / f"{dist.replace('-', '_')}-0.1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {dist}\nVersion: 0.1\n")
    lines = []
    for group, eps in entry_points.items():
        lines.append(f"[{group}]")
        lines += [f"{name} = {target}" for name, target in eps.items()]
    (info / "entry_points.txt").write_text("\n".join(lines) + "\n")


@pytest.fixture
def site(tmp_path, monkeypatch):
    root = tmp_path / "site"
    root.mkdir()
    monkeypatch.syspath_prepend(str(root))
    yield root
    for m in [m for m in sys.modules if m.startswith("fake_")]:
        del sys.modules[m]


def test_builtin_projects_are_registered():
    r = plugins.resolve(plugins.COMMANDS)
    assert {n for n, p in r.pieces.items() if p.builtin} == {"bench", "perception", "studio"}
    assert r.pieces["bench"].full_name == "medomni:bench"


def test_listed_without_import(site):
    make_dist(site, "medomni-one", "fake_one", {plugins.ENCODERS: {"enc-a": "fake_one.lazy:OBJ"}})
    r = plugins.resolve(plugins.ENCODERS)
    assert r.pieces["enc-a"].full_name == "medomni-one:enc-a"
    assert "fake_one.lazy" not in sys.modules
    assert r.pieces["enc-a"].load() is not None
    assert "fake_one.lazy" in sys.modules


def test_import_error_is_listed_and_others_load(site, capsys):
    make_dist(site, "medomni-one", "fake_one",
              {plugins.TOOLS: {"good": "fake_one:OBJ", "bad": "fake_one.missing:OBJ"}})
    assert main(["plugins"]) == 1
    out = capsys.readouterr().out
    assert "medomni-one:good" in out and "ok" in out
    assert "medomni-one:bad" in out and "cannot import fake_one.missing" in out


def test_plugin_command_runs(site, capsys):
    make_dist(site, "medomni-one", "fake_one", {plugins.COMMANDS: {"hello": "fake_one:group"}})
    assert main(["hello"]) == 0
    assert "ran fake_one" in capsys.readouterr().out
    assert main(["--help"]) == 0
    assert "hello" in capsys.readouterr().out


def test_clash_with_builtin_command_keeps_builtin(site, capsys):
    make_dist(site, "medomni-one", "fake_one", {plugins.COMMANDS: {"bench": "fake_one:group"}})
    r = plugins.resolve(plugins.COMMANDS)
    assert r.pieces["bench"].builtin and not r.errors
    assert any("medomni-one" in w and "kept medomni:bench" in w for w in r.warnings)
    assert main(["bench"]) == 0
    captured = capsys.readouterr()
    assert "usage: medomni bench" in captured.out and "ran fake_one" not in captured.out
    assert "warning: command 'bench' from medomni-one" in captured.err


def test_clash_with_core_command_is_skipped(site, capsys):
    make_dist(site, "medomni-one", "fake_one", {plugins.COMMANDS: {"cache": "fake_one:group"}})
    r = plugins.resolve(plugins.COMMANDS)
    assert "cache" not in r.pieces and r.warnings
    assert main(["cache"]) == 1  # Core's own command, still a placeholder
    assert "ran fake_one" not in capsys.readouterr().out


def test_clash_inside_a_kind_loads_neither(site):
    make_dist(site, "medomni-one", "fake_one", {plugins.ENCODERS: {"enc-x": "fake_one:OBJ"}})
    make_dist(site, "medomni-two", "fake_two", {plugins.ENCODERS: {"enc-x": "fake_two:OBJ"}})
    r = plugins.resolve(plugins.ENCODERS)
    assert "enc-x" not in r.pieces
    assert sorted(p.full_name for p, _ in r.errors) == ["medomni-one:enc-x", "medomni-two:enc-x"]


def test_clash_between_plugin_commands_loads_neither(site):
    make_dist(site, "medomni-one", "fake_one", {plugins.COMMANDS: {"foo": "fake_one:group"}})
    make_dist(site, "medomni-two", "fake_two", {plugins.COMMANDS: {"foo": "fake_two:group"}})
    r = plugins.resolve(plugins.COMMANDS)
    assert "foo" not in r.pieces and len(r.errors) == 2
    assert main(["foo"]) == 2


def test_plugin_agent_is_checked_against_its_contract(site, capsys):
    (site / "bad_agent.yaml").write_text("name: bad\nscaffold: terminus-2\nmodel: m\nroute: cloud\n"
                                         "model_served: m\nenv: {KEY: sk-literal}\n")
    (site / "good_agent.yaml").write_text("name: good\nscaffold: terminus-2\nmodel: m\nroute: local\nmodel_served: m\n")
    pkg = site / "fake_agents"
    make_dist(site, "medomni-agents", "fake_agents", {plugins.AGENTS: {"bad": "fake_agents:BAD", "good": "fake_agents:GOOD"}})
    (pkg / "__init__.py").write_text(f"BAD = {str(site / 'bad_agent.yaml')!r}\nGOOD = {str(site / 'good_agent.yaml')!r}\n")
    assert main(["plugins"]) == 1
    out = capsys.readouterr().out
    assert "medomni-agents:good" in out and "medomni-agents:bad" in out and "only as" in out
