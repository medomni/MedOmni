"""The family registry (part 3): 42 family files, each checked against its contract."""
import numpy as np
import pytest
import yaml

from medomni.core import contracts as c
from medomni.core import families
from tests.repro import migrate as convert
from tests.repro.migrate import families as fconv

FULL_SCALE = {d: (np.iinfo(d).min, np.iinfo(d).max) for d in ("int16", "uint8", "uint16")}


@pytest.fixture(scope="module")
def registry(repo):
    return families.load_registry(repo)


def test_all_family_files_load(registry, repo):
    assert len(registry) == 42
    stems = {p.stem for p in (repo / "core/families").glob("*.yaml")} - {"aliases"}
    assert set(registry) == stems
    assert families.get("spo2-series-10hz-pct", repo).protocol.range == (0.0, 100.0)


def test_every_family_has_a_dtype(registry):
    assert all(f.protocol.dtype for f in registry.values())


def test_ranges_are_ordered_and_inside_the_dtype(registry):
    ranged = {fid: f.protocol for fid, f in registry.items() if f.protocol.range is not None}
    assert set(ranged) == {"spo2-series-10hz-pct", "wearable-spo2-1min-pct"}
    for fid, p in ranged.items():
        low, high = p.range
        assert low < high
        if p.dtype in FULL_SCALE:
            assert FULL_SCALE[p.dtype][0] <= low and high <= FULL_SCALE[p.dtype][1], fid


# What Stage 3 part 1 changed in the converted family files: rates for 4 families (R-87, p13), and the 7 Chinese
# protocol values in English. Every other family file is still byte-identical to the converter's output.
STAGE3_EDITS = {
    "capnography-mmhg": {"rate_hz": 20}, "ppg-waveform-uncal": {"rate_hz": 100}, "resp-flow": {"rate_hz": 20},
    "snore-acoustic": {"rate_hz": 200},
    "octa-flowcube-mono8-3d": {"quantity": "flow decorrelation"}, "fundus-faf-mono8-2d": {"quantity": "autofluorescence"},
    "oct-bscanset-radial24-circle3-mono8": {"axis3": "24 radial lines + 3 concentric circles; not stackable"},
    "oct-volume-raster-mono8-3d": {"axis3": "parallel B-scans, slice spacing sd=0"},
    "flio-tcspc-256x256x1024bin-u16": {"axis3": "time, 1024 bins × 12.5 ps"},
    "retinal-heightmap-surfaces-f32": {"units": "depth", "axis3": "retinal surfaces, 2, 9, 10 or 11 by device"},
}


def test_committed_files_equal_the_converter(repo, v02_root):
    outputs, _ = fconv.convert(v02_root)
    edited = set()
    for rel, data in outputs.items():
        fid = rel.rsplit("/", 1)[-1].removesuffix(".yaml")
        if fid in STAGE3_EDITS:
            data["protocol"].update(STAGE3_EDITS[fid])
            assert yaml.safe_load((repo / rel).read_text(encoding="utf-8")) == data, f"{rel} has edits beyond Stage 3's"
            edited.add(fid)
        else:
            assert (repo / rel).read_text(encoding="utf-8") == convert.dump(data), f"{rel} differs from the converter"
    assert edited == set(STAGE3_EDITS)


def test_missing_folder_raises(tmp_path):
    with pytest.raises(families.FamilyError, match="folder missing"):
        families.load_registry(tmp_path)


def test_empty_folder_raises(tmp_path):
    (tmp_path / "core/families").mkdir(parents=True)
    with pytest.raises(families.FamilyError, match="no family files"):
        families.load_registry(tmp_path)


def test_id_must_match_the_file_name(tmp_path, repo):
    d = tmp_path / "core/families"
    d.mkdir(parents=True)
    data = yaml.safe_load((repo / "core/families/spo2-series-10hz-pct.yaml").read_text(encoding="utf-8"))
    (d / "other-name.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(families.FamilyError, match="differs from the file name"):
        families.load_registry(tmp_path)


def test_a_bad_file_is_an_error(tmp_path):
    d = tmp_path / "core/families"
    d.mkdir(parents=True)
    (d / "x.yaml").write_text("id: x\nread_by: direct\nstatus: declared\nprotocol: {format: [edf], ndim: 1}\n")
    with pytest.raises(c.ContractError, match="dtype"):
        families.load_registry(tmp_path)


def test_unknown_family(repo):
    with pytest.raises(families.FamilyError, match="unknown family"):
        families.get("no-such-family", repo)


def test_outside_a_repository_the_error_says_what_to_do(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(families.FamilyError, match="clone installed with `uv pip install -e .`"):
        families.load_registry()
