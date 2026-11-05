"""T1 tests run behind the guard: no data, no Docker, no network (see medomni.core.testing.guard)."""
from pathlib import Path

import pytest

from medomni.core.testing import guard

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def t1_guard(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("t1")
    with pytest.MonkeyPatch.context() as mp:
        guard.install(mp, repo=REPO, tmp=tmp)
        yield tmp


@pytest.fixture(scope="session")
def repo() -> Path:
    return REPO
