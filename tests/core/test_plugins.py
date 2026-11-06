"""Plug-in loading: lazy listing, import errors, name clashes (R-65), content folders (R-69)."""
import io
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from medomni.core import plugins
from medomni.core.cli import main
from medomni.core.contracts.check import check

from .contract_examples import CARD, EXAMPLES


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
    make_dist(site, "medomni-one", "fake_one", {plugins.TOOLS: {"enc-a": "fake_one.lazy:OBJ"}})
    r = plugins.resolve(plugins.TOOLS)
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
    assert main(["cache", "build", "x"]) == 1  # Core's own command; build is a placeholder until part 6
    assert "ran fake_one" not in capsys.readouterr().out


def test_clash_inside_a_kind_loads_neither(site):
    make_dist(site, "medomni-one", "fake_one", {plugins.CONVERTERS: {"enc-x": "fake_one:OBJ"}})
    make_dist(site, "medomni-two", "fake_two", {plugins.CONVERTERS: {"enc-x": "fake_two:OBJ"}})
    r = plugins.resolve(plugins.CONVERTERS)
    assert "enc-x" not in r.pieces
    assert sorted(p.full_name for p, _ in r.errors) == ["medomni-one:enc-x", "medomni-two:enc-x"]


def test_clash_between_plugin_commands_loads_neither(site):
    make_dist(site, "medomni-one", "fake_one", {plugins.COMMANDS: {"foo": "fake_one:group"}})
    make_dist(site, "medomni-two", "fake_two", {plugins.COMMANDS: {"foo": "fake_two:group"}})
    r = plugins.resolve(plugins.COMMANDS)
    assert "foo" not in r.pieces and len(r.errors) == 2
    assert main(["foo"]) == 2


def test_groups():
    assert plugins.GROUPS == ("medomni.commands", "medomni.checks", "medomni.converters", "medomni.tools",
                              "medomni.runners", "medomni.metrics")
    assert plugins.PLUGINS == "medomni.plugins"


# ---------------------------------------------------------------- content folders (R-69)

AGENT = "name: {n}\nscaffold: terminus-2\nmodel: m\nroute: local\nmodel_served: m\n"
BAD_AGENT = "name: bad\nscaffold: terminus-2\nmodel: m\nroute: cloud\nmodel_served: m\nenv: {KEY: sk-literal}\n"
DATASET = yaml.safe_dump(EXAMPLES["dataset-config"][0], sort_keys=False)


def make_plugin(site: Path, dist: str, module: str, files: dict[str, str], folder: str = "content") -> Path:
    """A plug-in whose package raises if imported, so any test that finds its folder proves nothing ran."""
    make_dist(site, dist, module, {plugins.PLUGINS: {"main": f"{module}:{folder}"}})
    (site / module / "__init__.py").write_text("raise RuntimeError('plug-in code ran')\n")
    for rel, text in files.items():
        f = site / module / "content" / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    return site / module / "content"


def test_folder_found_without_running_plugin_code(site):
    root = make_plugin(site, "medomni-one", "fake_one", {"bench/agents/a.yaml": AGENT.format(n="a")})
    (f,) = plugins.folders()
    assert (f.package, f.path, f.error) == ("medomni-one", root, None)
    assert "fake_one" not in sys.modules


def test_folder_in_a_sub_package(site):
    make_dist(site, "medomni-one", "fake_one", {plugins.PLUGINS: {"main": "fake_one.sub:data"}})
    (site / "fake_one" / "__init__.py").write_text("raise RuntimeError('plug-in code ran')\n")
    (site / "fake_one" / "sub" / "data").mkdir(parents=True)
    (site / "fake_one" / "sub" / "__init__.py").write_text("raise RuntimeError('plug-in code ran')\n")
    (f,) = plugins.folders()
    assert f.path == site / "fake_one" / "sub" / "data" and "fake_one" not in sys.modules


@pytest.mark.parametrize("target, message", [("fake_one", "must be"), ("fake_one:nope", "no folder 'nope'"),
                                             ("fake_none:content", "no package")])
def test_bad_folder_targets(site, target, message):
    make_dist(site, "medomni-one", "fake_one", {plugins.PLUGINS: {"main": target}})
    (f,) = plugins.folders()
    assert f.path is None and message in f.error


def test_zip_install_is_refused(tmp_path, monkeypatch):
    z = tmp_path / "site.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("fake_zip/__init__.py", "")
        zf.writestr("fake_zip/content/bench/agents/a.yaml", AGENT.format(n="a"))
        zf.writestr("medomni_zip-0.1.dist-info/METADATA", "Metadata-Version: 2.1\nName: medomni-zip\nVersion: 0.1\n")
        zf.writestr("medomni_zip-0.1.dist-info/entry_points.txt", "[medomni.plugins]\nmain = fake_zip:content\n")
    monkeypatch.syspath_prepend(str(z))
    (f,) = plugins.folders()
    assert f.path is None and "zip installs are not supported" in f.error


def test_pieces_by_kind(site, repo):
    make_plugin(site, "medomni-one", "fake_one", {
        "bench/agents/a.yaml": AGENT.format(n="a"),
        "bench/datasets/demo/dataset.yaml": DATASET,
        "bench/datasets/demo/hooks/labels.py": "raise RuntimeError('hook ran')\n",
        "perception/encoders/fam-x/enc-y/card.yaml": "id: fam-x__enc-y\n"})
    roots, bad = plugins.roots(repo)
    assert roots[0] == (plugins.BUILTIN, repo) and not bad
    kinds = plugins.content(roots)
    assert kinds["agents"].pieces["a"].full_name == "medomni-one:a"
    assert kinds["agents"].pieces["terminus-2-replay"].builtin  # the repository is built-in content
    assert kinds["datasets"].pieces["demo"].path.name == "demo"
    assert kinds["encoders"].pieces["fam-x__enc-y"].package == "medomni-one"


def test_plugin_content_is_checked_like_the_repository(site, repo, monkeypatch, capsys):
    card = yaml.safe_dump(CARD, sort_keys=False)
    make_plugin(site, "medomni-one", "fake_one", {
        "bench/agents/good.yaml": AGENT.format(n="good"),
        "bench/agents/bad.yaml": BAD_AGENT,
        "bench/datasets/demo/dataset.yaml": DATASET,
        "bench/datasets/demo/hooks/labels.py": "raise RuntimeError('hook ran')\n",
        "perception/encoders/cxr-radiograph-2d/demo/card.yaml": card,
        "core/families/x.yaml": "not: checked\n",  # families come from the repository only
    })
    counts, failed = check(repo, only=None, out=io.StringIO())
    assert failed == 1
    assert counts["model card"] == [1, 0] and counts["dataset config"] == [1, 0]
    monkeypatch.chdir(repo)
    assert main(["plugins"]) == 1
    out = capsys.readouterr().out
    assert "medomni.plugins" in out and "medomni-one" in out
    assert "agent     medomni-one:good" in out and " ok" in out
    assert "medomni-one:bad" in out and "only as" in out
    assert "encoder   medomni-one:cxr-radiograph-2d__demo" in out
    assert "fake_one" not in sys.modules


def test_content_clash_loads_neither(site, repo, monkeypatch, capsys):
    make_plugin(site, "medomni-one", "fake_one", {"bench/agents/same.yaml": AGENT.format(n="same"),
                                                  "bench/agents/terminus-2-replay.yaml": AGENT.format(n="r")})
    make_plugin(site, "medomni-two", "fake_two", {"bench/agents/same.yaml": AGENT.format(n="same")})
    agents = plugins.content(plugins.roots(repo)[0])["agents"]
    assert "same" not in agents.pieces and "terminus-2-replay" not in agents.pieces
    assert sorted(p.full_name for p, _ in agents.errors) == [
        "medomni-one:same", "medomni-one:terminus-2-replay", "medomni-two:same", "medomni:terminus-2-replay"]
    monkeypatch.chdir(repo)
    assert main(["plugins"]) == 1
    out = capsys.readouterr().out
    assert "medomni:terminus-2-replay" in out and "none is loaded" in out
