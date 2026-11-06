"""The family registry (part 3): 42 family files, each checked against its contract."""
import numpy as np
import pytest
import yaml

from medomni.core import contracts as c
from medomni.core import families
from medomni.core.contracts import convert
from medomni.core.contracts.convert import families as fconv

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


def test_committed_files_equal_the_converter(repo):
    outputs, _ = fconv.convert(repo)
    for rel, data in outputs.items():
        assert (repo / rel).read_text(encoding="utf-8") == convert.dump(data), f"{rel} differs from the converter"
    assert (repo / fconv.ALIAS_DEST).read_text(encoding="utf-8") == fconv.aliases(repo)


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
