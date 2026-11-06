"""Family converters (part 3): registered by entry point, checked on load, one name per converter (R-65)."""
import hashlib
import sys

import numpy as np
import pytest

from medomni.core import families, plugins
from medomni.core.families import converters

from .test_plugins import make_dist

DUMMY = '''
import hashlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pyedflib

from medomni.core.families.converters import ConvertFacts


class NpyToEdf:
    """Dummy converter for tests: a (channels, samples) int16 .npy array -> an EDF with the family's channels."""

    name = "npy-to-edf"
    version = "1"
    source_format = "npy"
    families = frozenset({"spo2-series-10hz-pct"})

    def convert(self, src, family, out):
        x = np.load(src)
        p = family.protocol
        w = pyedflib.EdfWriter(str(out), len(p.channels), file_type=pyedflib.FILETYPE_EDFPLUS)
        w.setStartdatetime(datetime(2150, 1, 1))  # a fixed header time: the same input gives the same bytes (R-39)
        w.setSignalHeaders([{"label": ch, "dimension": p.units or "", "sample_frequency": p.rate_hz,
                             "physical_min": -32768, "physical_max": 32767,
                             "digital_min": -32768, "digital_max": 32767} for ch in p.channels])
        w.writeSamples([row.astype(np.int32) for row in x], digital=True)
        w.close()
        return ConvertFacts(Path(out), hashlib.sha256(Path(out).read_bytes()).hexdigest())


CONVERTER = NpyToEdf()
'''


@pytest.fixture
def site(tmp_path, monkeypatch):
    root = tmp_path / "site"
    root.mkdir()
    monkeypatch.syspath_prepend(str(root))
    yield root
    for m in [m for m in sys.modules if m.startswith("fake_")]:
        del sys.modules[m]


def _install(site, dist, module, name="npy-to-edf"):
    make_dist(site, dist, module, {plugins.CONVERTERS: {name: f"{module}:CONVERTER"}})
    (site / module / "__init__.py").write_text(DUMMY)


def test_dummy_converter_registers_and_converts(site, repo, tmp_path):
    import pyedflib

    _install(site, "medomni-one", "fake_one")
    found = converters.load()
    assert not found.errors and set(found.found) == {"npy-to-edf"}
    conv = converters.for_family("spo2-series-10hz-pct", "npy", found)
    src = tmp_path / "x.npy"
    np.save(src, np.array([[90, 95, 97, 99] * 25], dtype=np.int16))
    facts = conv.convert(src, families.get("spo2-series-10hz-pct", repo), tmp_path / "x.edf")
    assert facts.sha256 == hashlib.sha256(facts.path.read_bytes()).hexdigest()
    r = pyedflib.EdfReader(str(facts.path))
    try:
        assert r.getSignalLabels() == ["spo2"] and r.getSampleFrequency(0) == 10
        assert list(r.readSignal(0, digital=True)[:4]) == [90, 95, 97, 99]
    finally:
        r.close()


def test_same_name_twice_is_refused(site):
    _install(site, "medomni-one", "fake_one")
    _install(site, "medomni-two", "fake_two")
    found = converters.load()
    assert not found.found and len(found.errors) == 2 and all("none is loaded" in e for e in found.errors)
    with pytest.raises(LookupError, match="0 converters"):
        converters.for_family("spo2-series-10hz-pct", "npy", found)


def test_name_must_match_the_entry_point(site):
    _install(site, "medomni-one", "fake_one", name="other-name")
    found = converters.load()
    assert not found.found and "names itself 'npy-to-edf'" in found.errors[0]


def test_a_converter_is_deterministic(site, tmp_path, repo):
    """The same input must give the same bytes, or two users' cache content hashes differ (R-39)."""
    _install(site, "medomni-one", "fake_one")
    conv = converters.for_family("spo2-series-10hz-pct", "npy")
    src = tmp_path / "x.npy"
    np.save(src, np.array([[95, 96, 97] * 100], dtype=np.int16))
    fam = families.get("spo2-series-10hz-pct", repo)
    a, b = (conv.convert(src, fam, tmp_path / f"{n}.edf") for n in "ab")
    assert a.sha256 == b.sha256


def test_not_a_converter(site):
    make_dist(site, "medomni-one", "fake_one", {plugins.CONVERTERS: {"x": "fake_one:OBJ"}})
    found = converters.load()
    assert not found.found and "not a family converter" in found.errors[0]
