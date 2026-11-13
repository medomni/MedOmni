"""Outside paths for the T3/T4 tests here: taken only from environment variables, never defaulted.

A test that needs a path skips when its variable is unset. `needs` is a skipif mark, so T1 runs, which deselect
these tests, never see a skip.
"""
import os
from pathlib import Path

import pytest

V02 = "MEDOMNI_V02"  # v0.2.1's working checkout, with its run outputs
WORKSPACE = "MEDOMNI_STAGE3_WORKSPACE"  # a v0.3 workspace.yaml with the real copies
REPRO_TASKS = "MEDOMNI_REPRO_TASKS"  # where check 3 builds its tasks
BASELINE_SCORES = "MEDOMNI_BASELINE_SCORES"  # the v0.2.1 baseline run check 5 re-scores
BASELINE_ENCODERS = "MEDOMNI_BASELINE_ENCODERS"  # the v0.2.1 baseline run whose encoder rows check 4 replays


def env(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value) if value else None


def needs(*names: str):
    missing = [n for n in names if not os.environ.get(n)]
    return pytest.mark.skipif(bool(missing), reason=f"set {', '.join(missing)} to run this test")
