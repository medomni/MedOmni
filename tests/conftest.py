"""T1 tests run behind the guard: no data, no Docker, no network (see medomni.core.testing.guard)."""
import subprocess
from pathlib import Path

import pytest

from medomni.core.testing import guard

REPO = Path(__file__).resolve().parents[1]


T2_T4 = ("containers", "data", "baseline")  # pytest.ini markers; plain `pytest` deselects all three


def _t1_only(config) -> bool:
    """True when the marker expression keeps every T2-T4 test out, as plain `pytest` does."""
    expr = config.option.markexpr or ""
    return all(f"not {m}" in expr for m in T2_T4)


@pytest.fixture(scope="session", autouse=True)
def t1_guard(tmp_path_factory, request):
    """The guard holds for T1 sessions only; `-m containers` (or data, baseline) runs without it."""
    tmp = tmp_path_factory.mktemp("t1")
    if not _t1_only(request.config):
        yield tmp
        return
    with pytest.MonkeyPatch.context() as mp:
        guard.install(mp, repo=REPO, tmp=tmp)
        yield tmp


@pytest.fixture(scope="session")
def repo() -> Path:
    return REPO


@pytest.fixture(scope="session")
def v02_root(tmp_path_factory) -> Path:
    """v0.2.1's files, out of this repository's git history: the v0.2 side of the equivalence tests."""
    from tests.repro.migrate import V02_COMMIT, v02_tree

    if subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{V02_COMMIT}^{{commit}}"]).returncode:
        pytest.fail(f"v0.2.1's commit {V02_COMMIT} is not in this clone's history; fetch it (git fetch --tags)")
    return v02_tree(REPO, tmp_path_factory.mktemp("v02"))
