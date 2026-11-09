"""The `.vital` converter on a dummy recording passes each family's own check (R-9). No real data."""
import numpy as np
import pytest

from medomni.core import families
from medomni.core.families import check, vital_to_wfdb as v


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    root = tmp_path_factory.mktemp("vital")
    p = root / "cases" / "1.vital"
    v.write_dummy(p, 6, np.random.default_rng(0))
    (root / "clinical_info.csv").write_text("caseid,opend\n1,4\n")
    return p


@pytest.mark.parametrize("family", sorted(v.TRACKS))
def test_each_family_passes_its_check_and_is_cut_at_the_end_of_the_operation(case, family, tmp_path):
    f = v.CONVERTER.convert(case, family, tmp_path / f"{family}.edf")
    assert check.conforms(families.get(family), f.path) == []
    if f.path.suffix == ".edf":
        import pyedflib

        with pyedflib.EdfReader(str(f.path)) as r:
            assert r.getFileDuration() <= 4
    else:
        import wfdb

        rec = wfdb.rdheader(str(f.path.with_suffix("")))
        assert rec.sig_len / rec.fs <= 4


def test_conversion_is_deterministic(case, tmp_path):
    a = v.CONVERTER.convert(case, "ppg-waveform-uncal", tmp_path / "a" / "x.edf")
    b = v.CONVERTER.convert(case, "ppg-waveform-uncal", tmp_path / "b" / "x.edf")
    assert a.sha256 == b.sha256
