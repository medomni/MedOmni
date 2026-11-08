"""The `medomni` command: lazy help, version, project commands."""
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

import pytest

MEDOMNI = Path(sys.executable).parent / "medomni"
LISTED = ("plugins", "contracts", "cache", "bench", "perception", "studio")
NOT_IMPORTED = ("medomni.bench", "medomni.perception", "medomni.studio", "pandas", "pyarrow")

PROBE = """
import sys
from medomni.core.cli import main
rc = main(sys.argv[1:])
heavy = sorted(m for m in sys.modules if m.split('.')[0] in ('pandas', 'pyarrow')
               or m.startswith(('medomni.bench', 'medomni.perception', 'medomni.studio')))
print('IMPORTED', ' '.join(heavy) or '-', file=sys.stderr)
sys.exit(rc)
"""


def run(*args, probe=False):
    cmd = [sys.executable, "-c", PROBE, *args] if probe else [str(MEDOMNI), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2])


def test_script_is_installed():
    assert MEDOMNI.exists(), "run `uv sync`: the medomni script is missing"


def test_help_lists_commands():
    r = run("--help")
    assert r.returncode == 0, r.stderr
    for name in LISTED:
        assert f"  {name} " in r.stdout, name


def test_help_imports_no_project():
    r = run("--help", probe=True)
    assert r.returncode == 0, r.stderr
    assert "IMPORTED -" in r.stderr, r.stderr


def test_help_is_fast():
    def best(args):
        times = []
        for _ in range(3):
            t = time.perf_counter()
            subprocess.run([sys.executable, *args], capture_output=True, check=True)
            times.append(time.perf_counter() - t)
        return min(times)

    bare = best(["-c", "pass"])
    full = best(["-c", "from medomni.core.cli import main; main(['--help'])"])
    assert full - bare < 0.2, f"--help adds {full - bare:.3f} s to interpreter start"


def test_version():
    r = run("--version")
    assert r.returncode == 0 and r.stdout.strip() == f"medomni {version('medomni')}"


@pytest.mark.parametrize("project", ["bench", "perception", "studio"])
def test_project_command_runs(project):
    r = run(project)
    assert r.returncode == 0, r.stderr
    assert f"usage: medomni {project}" in r.stdout
    expected = {"bench": "<command>", "perception": "No commands yet.", "studio": "dummy"}[project]
    assert expected in r.stdout


@pytest.mark.parametrize("args,part", [(["data", "check", "mimic-iv"], 2), (["task", "build", "--set", "medomni-bench/v1"], 3),
                                       (["task", "check", "--set", "medomni-bench/v1"], 4),
                                       (["task", "check", "--release"], 4), (["run", "--agent", "a", "--set", "x/y"], 5),
                                       (["score", "--set", "x/y"], 5)])
def test_bench_stub_names_its_part(args, part):
    r = run("bench", *args)
    assert r.returncode == 2 and f"not built yet (Stage 3 part {part})" in r.stderr


def test_cache_build_needs_a_workspace():
    r = run("cache", "build", "dummy-mimic")
    assert r.returncode == 2 and "no workspace config" in r.stderr


def test_contracts_check_runs():
    r = run("contracts", "check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "files pass" in r.stdout


def test_unknown_command():
    r = run("nope")
    assert r.returncode == 2 and "unknown command 'nope'" in r.stderr
