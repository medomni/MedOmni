"""Checking files in draw order picks the same patients as checking the whole pool first."""
import random
from types import SimpleNamespace as NS

import pytest

from medomni.bench.build.pool import BuildError, Patient, Pool, draw


def _pool(n, seed):
    rng = random.Random(seed)
    cohort = NS(select=NS(by=["y"], balance=[], n=20, seed=7))
    patients = {f"p{i}": Patient(f"p{i}", NS(anchor=f"t{i}"), {"y": rng.randint(0, 1)}, {}) for i in range(n)}
    return Pool(NS(id="t@n20", cohort=cohort), patients)


@pytest.mark.parametrize("seed", range(20))
def test_same_patients_as_checking_everyone(seed):
    fail = {f"p{i}" for i in random.Random(seed).sample(range(300), 60)}
    whole = _pool(300, seed)
    whole.patients = {k: v for k, v in whole.patients.items() if k not in fail}
    seen = []

    def check(batch):
        seen.extend(p.id for p in batch)
        return {p.id for p in batch} - fail

    walked = _pool(300, seed)
    assert draw(walked, check) == draw(whole)
    assert len(seen) == len(set(seen)) < 300  # nobody twice, and not the whole pool
    assert walked.counts["file check tried"] == len(seen)
    assert walked.counts["file check"] == 300 - len(fail & set(seen))


def test_refuses_when_too_few_convert():
    pool = _pool(30, 1)
    with pytest.raises(BuildError, match="whose files convert"):
        draw(pool, lambda batch: set())
