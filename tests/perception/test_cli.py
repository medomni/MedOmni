"""`medomni perception`: the commands parse, `new` writes a folder the card check accepts, and `check` stops at a
bad card before any build. No Docker."""
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from medomni.perception import cli, registry


def run(*args):
    medomni = Path(sys.executable).with_name("medomni")  # the installed console script, as Core's CLI tests use
    return subprocess.run([str(medomni), "perception", *args], capture_output=True, text=True)


def test_help_lists_the_four_commands():
    r = run("--help")
    assert r.returncode == 0
    for cmd in ("pull", "up", "new", "check"):
        assert cmd in r.stdout


def test_documented_forms_parse():
    a = cli._parser().parse_args(["check", "perception/encoders/x/y", "--samples", "/tmp/families", "--freeze"])
    assert (a.folder, a.samples, a.freeze) == (Path("perception/encoders/x/y"), Path("/tmp/families"), True)
    assert cli._parser().parse_args(["up", "--data-root", "/srv/data"]).data_root == "/srv/data"
    assert cli._parser().parse_args(["pull", "cxr-radiograph-2d"]).targets == ["cxr-radiograph-2d"]


def test_new_writes_a_folder_the_card_check_accepts(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as root:
        monkeypatch.setattr(registry, "encoders_root", lambda repo=None: Path(root))
        assert cli.group(["new", "cgm-5min-mgdl/my-encoder"]) == 0
        edir = Path(root) / "cgm-5min-mgdl/my-encoder"
        assert (edir / "testdata").is_dir() and (edir / "Dockerfile.dockerignore").is_file()
        errors, _ = registry.cards.check(edir)
        assert errors == []
        assert cli.group(["new", "cgm-5min-mgdl/my-encoder"]) == 2  # never overwrites
        assert cli.group(["new", "no-such-family/x"]) == 2


def test_check_refuses_a_bad_card_before_building(capsys):
    with tempfile.TemporaryDirectory() as root:
        edir = Path(root) / "cgm-5min-mgdl/bad"
        edir.mkdir(parents=True)
        (edir / "card.yaml").write_text("id: cgm-5min-mgdl__bad\nfamily: cgm-5min-mgdl\n")
        assert cli.group(["check", str(edir)]) == 1
        assert "card REJECTED" in capsys.readouterr().out


@pytest.mark.containers
def test_check_passes_on_a_shipped_encoder():
    from ._gateway import ENCODERS

    assert cli.group(["check", str(ENCODERS / "cgm-5min-mgdl/pyagata")]) == 0
