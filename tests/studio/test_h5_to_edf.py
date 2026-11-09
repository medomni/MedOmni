"""The h5-to-edf family converter (v0.2's bridge, R-19, R-105, R-110) on a planted night: no real data."""
import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from medomni.core.families import converters, h5_to_edf

REPO = Path(__file__).resolve().parents[2]
V02_BRIDGE = REPO / "data_task/familybridge/bridge.py"


def _night(path, signals, meas_date="2080-01-01 22:00:00", fs=200, seconds=30):
    import h5py

    rng = np.random.default_rng(7)
    with h5py.File(path, "w") as f:
        if meas_date:
            f.attrs["meas_date"] = meas_date
        g = f.create_group("signals")
        for name in signals:
            d = g.create_dataset(name, data=rng.integers(-2000, 2000, fs * seconds + 37, dtype=np.int16))
            d.attrs.update({"fs": fs, "unit": "uV", "phys_min": -3276.8, "phys_max": 3276.7,
                            "dig_min": -32768, "dig_max": 32767})
    return path


def _edf(path):
    import pyedflib

    r = pyedflib.EdfReader(str(path))
    try:
        return ([r.getLabel(i) for i in range(r.signals_in_file)], [r.getSampleFrequency(i) for i in range(r.signals_in_file)],
                [r.readSignal(i, digital=True) for i in range(r.signals_in_file)], r.getStartdatetime())
    finally:
        r.close()


def test_registered_and_found():
    found = converters.load()
    assert "h5-to-edf" in found.found and not found.errors
    assert converters.for_family("eog-2ch-200hz-uv", "h5", found).name == "h5-to-edf"


def test_channels_by_alias_whole_seconds(tmp_path):
    src = _night(tmp_path / "n.h5", ["E1", "e2", "chin"])  # e2 by alias, E1 by alias after no exact match
    with pytest.raises(h5_to_edf.Absent):  # v0.2's rule is case-sensitive: "E1" is no supply for e1-m2
        h5_to_edf.CONVERTER.convert(src, "eog-2ch-200hz-uv", tmp_path / "out.edf")
    src = _night(tmp_path / "m.h5", ["e1", "e2", "chin"])
    facts = h5_to_edf.CONVERTER.convert(src, "eog-2ch-200hz-uv", tmp_path / "out.edf")
    labels, rates, data, start = _edf(facts.path)
    assert labels == ["E1-M2", "E2-M1"] and rates == [200.0, 200.0]
    assert all(len(x) == 200 * 30 for x in data)  # cut to whole seconds
    assert str(start) == "2080-01-01 22:00:00"  # EDF keeps two-digit years (1985-2084)
    assert facts.sha256 == hashlib.sha256(facts.path.read_bytes()).hexdigest()


def test_roles_are_optional_but_one_is_needed(tmp_path):
    out = tmp_path / "out.edf"
    h5_to_edf.CONVERTER.convert(_night(tmp_path / "a.h5", ["leg-left"]), "emg-limb-200hz-uv", out)
    assert _edf(out)[0] == ["LEG-LEFT"]
    with pytest.raises(h5_to_edf.Absent, match="no role supply"):
        h5_to_edf.CONVERTER.convert(_night(tmp_path / "b.h5", ["e1"]), "emg-limb-200hz-uv", out)


def test_deterministic_without_meas_date(tmp_path):
    """v0.2 wrote the wall clock here (27 cached entries, p09); a converter gives the same bytes every time."""
    src = _night(tmp_path / "n.h5", ["e1", "e2"], meas_date=None)
    a = h5_to_edf.CONVERTER.convert(src, "eog-2ch-200hz-uv", tmp_path / "a.edf")
    b = h5_to_edf.CONVERTER.convert(src, "eog-2ch-200hz-uv", tmp_path / "b.edf")
    assert a.sha256 == b.sha256 and _edf(a.path)[3] == h5_to_edf.FIXED_START


def test_key_params_hash_only_what_the_conversion_reads():
    p = h5_to_edf.CONVERTER.params("eog-2ch-200hz-uv")
    assert p["family"] == "eog-2ch-200hz-uv" and len(p["reads"]) == 64
    assert set(h5_to_edf.reads("eog-2ch-200hz-uv")) == {"channels", "roles", "accepts"}  # no rate, units, dtype, range


@pytest.mark.skipif(not V02_BRIDGE.exists(), reason="v0.2's bridge is deleted in Stage 3 part 8")
@pytest.mark.parametrize("family,signals", [("eog-2ch-200hz-uv", ["e1", "e2"]), ("emg-limb-200hz-uv", ["leg-left", "arm-right"])])
def test_same_bytes_as_v02_bridge(tmp_path, family, signals):
    import yaml

    spec = importlib.util.spec_from_file_location("v02_bridge", V02_BRIDGE)
    v02 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v02)
    src = _night(tmp_path / "n.h5", signals)
    proto = yaml.safe_load((REPO / f"core/families/{family}.yaml").read_text())["protocol"]
    alias = yaml.safe_load((REPO / "core/families/aliases.yaml").read_text())
    v02.h5_to_family_edf(src, tmp_path / "v02.edf", family, proto, alias)
    new = h5_to_edf.CONVERTER.convert(src, family, tmp_path / "v03.edf")
    assert new.path.read_bytes() == (tmp_path / "v02.edf").read_bytes()
