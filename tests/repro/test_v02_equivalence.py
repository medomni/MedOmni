"""Core and Studio give v0.2's results where stored values or built files depend on them: the family aliases, the
quick hash, and the h5-to-edf conversion. v0.2's code is read from v0.2.1's files in git history (`v02_root`); no data.
"""
import datetime
import hashlib
import importlib.util
from pathlib import Path

import pytest
import yaml

from medomni.core import families, hashing
from medomni.core.families import aliases
from medomni.core.families.check import conforms
from medomni.core.families.dummy import signal
from tests.studio.test_h5_to_edf import _night, h5_to_edf

REPO = Path(__file__).resolve().parents[2]


def _v02(root: Path, rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, root / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def bridge(v02_root):
    return _v02(v02_root, "data_task/familybridge/bridge.py", "v02_bridge")


# ---------------------------------------------------------------- family aliases

GENERATED = "perception/runtime/family_alias.generated.yaml"
# Rates Stage 3 part 1 added (R-87, p13): the only change to v0.2's aliases. Rates are not in the bridge key (R-86).
STAGE3_RATES = {"resp-flow": [10, 50, 100, 200], "capnography-mmhg": [2, 10], "snore-acoustic": [500]}


@pytest.fixture(scope="module")
def v02(v02_root):
    return yaml.safe_load((v02_root / GENERATED).read_text(encoding="utf-8"))["families"]


def test_resolver_equals_v02_generated(repo, v02):
    assert len(v02) == 13
    for fid, want in v02.items():
        got = aliases.resolve(fid, repo)
        assert got.labels == want["labels"], fid
        assert got.components == want["components"], fid
        assert list(got.rates) == sorted(float(r) for r in want["rates"] + STAGE3_RATES.get(fid, [])), fid
        assert list(got.prefixes) == want["prefixes"], fid
        assert list(got.colors) == want["colors"], fid


def test_families_without_aliases_resolve_empty(repo, v02):
    rest = sorted(set(families.load_registry(repo)) - set(v02))
    assert len(rest) == 29
    for fid in rest:
        rates = tuple(sorted(float(r) for r in STAGE3_RATES.get(fid, [])))
        assert aliases.resolve(fid, repo) == aliases.ResolvedAliases(rates=rates)


def test_accepts_keep_v02_order_and_spelling(repo, v02_root):
    """U2.2: v0.2's accepts lists, in order and spelling, plus only the rates Stage 3 added (R-87)."""
    new = yaml.safe_load((repo / "core/families/aliases.yaml").read_text(encoding="utf-8"))
    old = yaml.safe_load((v02_root / "data_task/family_alias.yaml").read_text(encoding="utf-8"))
    assert new["families"]["resp-flow"]["accepts"][0].pop("rates") == STAGE3_RATES["resp-flow"]
    for fid in ("capnography-mmhg", "snore-acoustic"):
        assert new["families"].pop(fid) == {"accepts": [{"rates": STAGE3_RATES[fid]}]}
    assert new == old


# ---------------------------------------------------------------- the quick hash

MIB = 1 << 20
SIZES = [0, 10, MIB - 1, MIB, MIB + 1, 3 * MIB // 2, 2 * MIB, 2 * MIB + 1, 5 * MIB]
IN_BAND = {MIB + 1, 3 * MIB // 2, 2 * MIB}  # where the bridge's copy reads a tail and the others don't


@pytest.fixture(scope="module")
def sized(tmp_path_factory):
    d = tmp_path_factory.mktemp("sized")
    for n in SIZES:
        (d / f"f{n}").write_bytes(hashlib.shake_256(str(n).encode()).digest(n) if n else b"")  # head and tail differ
    return d


@pytest.mark.parametrize("n", SIZES)
def test_quick_sha_equals_the_stored_recipe(v02_root, bridge, sized, n):
    manifestbuilder = _v02(v02_root, "data_task/manifestbuilder/__init__.py", "v02_manifestbuilder")
    p = sized / f"f{n}"
    assert hashing.quick_sha(p) == manifestbuilder.quick_sha(p)
    assert len(hashing.quick_sha(p)) == 16
    if n not in IN_BAND:
        assert hashing.quick_sha(p) == bridge.quick_sha(p)
    else:
        assert hashing.quick_sha(p) != bridge.quick_sha(p)  # the one known difference (U2.3)


# ---------------------------------------------------------------- h5 to family EDF

BRIDGED = ["body-position-code-10hz", "ecg-1lead-200hz-uv", "eeg-sleep-6ch-200hz-uv", "emg-chin-200hz-uv",
           "emg-limb-200hz-uv", "eog-2ch-200hz-uv", "psg-cardiorespiratory-4ch-200hz-mixed", "pulse-rate-10hz-bpm",
           "resp-effort-rip-2ch-50hz", "spo2-series-10hz-pct"]


def test_bridge_round_trip(tmp_path, v02_root, bridge):
    """The dummy h5 night goes through v0.2's bridge, and each family EDF it makes conforms (the bridge read-only)."""
    alias = yaml.safe_load((v02_root / "data_task/family_alias.yaml").read_text(encoding="utf-8"))
    fams = [families.get(f, REPO) for f in BRIDGED]
    h5 = tmp_path / "night.h5"
    signal.write_h5(fams, 1, h5, subject="DUMMY-1", start=datetime.datetime(2150, 1, 1))
    for fam in fams:
        proto = yaml.safe_load((v02_root / f"data_task/families/{fam.id}.yaml").read_text(encoding="utf-8"))["protocol"]
        out = tmp_path / f"{fam.id}.edf"
        bridge.h5_to_family_edf(h5, out, fam.id, proto, alias)
        assert conforms(fam, out) == [], fam.id


@pytest.mark.parametrize("family,signals", [("eog-2ch-200hz-uv", ["e1", "e2"]), ("emg-limb-200hz-uv", ["leg-left", "arm-right"])])
def test_same_bytes_as_v02_bridge(tmp_path, bridge, family, signals):
    src = _night(tmp_path / "n.h5", signals)
    proto = yaml.safe_load((REPO / f"core/families/{family}.yaml").read_text())["protocol"]
    alias = yaml.safe_load((REPO / "core/families/aliases.yaml").read_text())
    bridge.h5_to_family_edf(src, tmp_path / "v02.edf", family, proto, alias)
    new = h5_to_edf.CONVERTER.convert(src, family, tmp_path / "v03.edf")
    assert new.path.read_bytes() == (tmp_path / "v02.edf").read_bytes()
