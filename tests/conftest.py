"""T1 tests run behind the guard: no data, no Docker, no network (see medomni.core.testing.guard)."""
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
