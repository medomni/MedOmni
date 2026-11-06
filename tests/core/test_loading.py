"""Loading (part 6): dummy datasets load into an event table; each step stops with a named error."""
import json
import shutil

import pytest
import yaml

from medomni.core.contracts import EventTable, load as load_contract
from medomni.core.families.dummy.datasets import INT_BASE, make_dataset
from medomni.core.loading import DESCRIPTION, LoadError, load
from medomni.core.testing import DATASETS

SHAPES = ("dummy-mimic", "dummy-omop", "dummy-bdsp")


def rows(path):
    import pyarrow.parquet as pq

    return pq.read_table(path).to_pylist()


@pytest.fixture(scope="module")
def raw(tmp_path_factory):
    out = tmp_path_factory.mktemp("raw")
    return {s: make_dataset(DATASETS / s, out / s, subjects=4) for s in SHAPES}


@pytest.fixture(scope="module")
def loaded(raw, tmp_path_factory):
    out = tmp_path_factory.mktemp("loaded")
    return {s: load(DATASETS / s, raw[s].root, out / s) for s in SHAPES}


@pytest.mark.parametrize("shape", SHAPES)
def test_dummy_datasets_load(raw, loaded, shape):
    r = loaded[shape]
    events = rows(r.path)
    assert r.rows == len(events) > 0 and r.subjects == 4
    desc = load_contract(r.path.parent / DESCRIPTION, EventTable)
    assert desc.rows == r.rows and desc.subjects == 4
    files = [e for e in events if e["code"].startswith("FILE//")]
    on_disk = {p.relative_to(raw[shape].root).as_posix() for p in raw[shape].root.rglob("*")
               if p.is_file() and p.suffix in (".hea", ".png", ".dcm", ".json", ".h5")}
    assert {e["path"] for e in files} == on_disk
    assert all(e["sha256"] and len(e["sha256"]) == 64 for e in files)
    if shape == "dummy-bdsp":  # one h5 night carries 10 families: one FILE row per family
        assert len(files) == 4 * 10


def test_times_follow_the_dataset_time_kind(loaded):
    mimic = [e["time"] for e in rows(loaded["dummy-mimic"].path) if e["time"]]
    omop = [e["time"] for e in rows(loaded["dummy-omop"].path) if e["time"]]
    assert all("T" in t for t in mimic)
    assert all(len(t) == 10 for t in omop)  # visit dates: dates only


def test_reserved_ids_survive_the_event_table(raw, loaded):
    """R-74: ids above 2^32 come out of the loader and the Parquet table unchanged."""
    ids = {e["subject_id"] for e in rows(loaded["dummy-mimic"].path)}
    assert ids == {str(s) for s in raw["dummy-mimic"].subjects}
    assert min(int(i) for i in ids) > max(2 ** 32, INT_BASE)


def test_determinism(raw, tmp_path):
    a = load(DATASETS / "dummy-mimic", raw["dummy-mimic"].root, tmp_path / "a")
    b = load(DATASETS / "dummy-mimic", raw["dummy-mimic"].root, tmp_path / "b")
    assert a.path.read_bytes() == b.path.read_bytes()


def test_filters_read_less(raw, tmp_path):
    full = load(DATASETS / "dummy-mimic", raw["dummy-mimic"].root, tmp_path / "full")
    only = load(DATASETS / "dummy-mimic", raw["dummy-mimic"].root, tmp_path / "labs", tables={"labevents"})
    assert set(only.rows_read) == {"labevents"} and only.rows_read["labevents"] == full.rows_read["labevents"]
    assert {e["code"].split("//")[0] for e in rows(only.path)} == {"LAB"}
    fam = load(DATASETS / "dummy-bdsp", raw["dummy-bdsp"].root, tmp_path / "fam", families={"spo2-series-10hz-pct"})
    assert {e["code"] for e in rows(fam.path) if e["code"].startswith("FILE//")} == {"FILE//spo2-series-10hz-pct"}
    codes = load(DATASETS / "dummy-mimic", raw["dummy-mimic"].root, tmp_path / "codes", codes=("^DIAGNOSIS//",))
    assert {e["code"][:11] for e in rows(codes.path)} == {"DIAGNOSIS//"}


def _copy(tmp_path, shape="dummy-mimic"):
    pkg = tmp_path / shape
    shutil.copytree(DATASETS / shape, pkg)
    return pkg


def test_verify_names_a_missing_file(raw, tmp_path):
    root = tmp_path / "raw"
    shutil.copytree(raw["dummy-mimic"].root, root)
    (root / "hosp/labevents.csv").unlink()
    with pytest.raises(LoadError, match="verify: .*hosp/labevents.csv"):
        load(DATASETS / "dummy-mimic", root, tmp_path / "out")


def test_check_names_an_unknown_code(raw, tmp_path):
    pkg = _copy(tmp_path)
    codes = (pkg / "codes.csv").read_text().splitlines()
    (pkg / "codes.csv").write_text("\n".join(l for l in codes if not l.startswith("LAB//90002")) + "\n")
    with pytest.raises(LoadError, match="check: labevents.*LAB//90002"):
        load(pkg, raw["dummy-mimic"].root, tmp_path / "out")


def test_check_names_an_unknown_family(raw, tmp_path):
    pkg = _copy(tmp_path)
    cfg = yaml.safe_load((pkg / "dataset.yaml").read_text())
    cfg["read"][1]["options"]["files"]["no-such-family"] = cfg["read"][1]["options"]["files"].pop("cxr-radiograph-2d")
    (pkg / "dataset.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    with pytest.raises(LoadError, match="unknown family no-such-family"):
        load(pkg, raw["dummy-mimic"].root, tmp_path / "out")


def _with_rules(tmp_path, rules):
    pkg = _copy(tmp_path, "dummy-omop")
    cfg = yaml.safe_load((pkg / "dataset.yaml").read_text())
    cfg["rules"] = rules
    (pkg / "dataset.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    return pkg


def test_rules_one_visit_and_untimed(raw, tmp_path):
    pkg = _with_rules(tmp_path, {"one_visit": "VISIT", "untimed": True})
    events = rows(load(pkg, raw["dummy-omop"].root, tmp_path / "out").path)
    visits = {e["subject_id"]: (e["visit_id"], e["time"]) for e in events if e["code"] == "VISIT"}
    for e in events:
        assert e["visit_id"] == visits[e["subject_id"]][0]
        if e["code"].startswith(("GENDER//", "YEAR_OF_BIRTH")):  # untimed facts take the visit's time
            assert e["time"] == visits[e["subject_id"]][1]


def test_rules_visit_unit(raw, tmp_path):
    pkg = _with_rules(tmp_path, {"visit": "unit"})
    assert all(e["visit_id"] == e["subject_id"] for e in rows(load(pkg, raw["dummy-omop"].root, tmp_path / "o").path))


@pytest.mark.parametrize("rules, match", [({"one_visit": "GENDER//F"}, "no GENDER//F event"),
                                          ({"untimed": True}, "untimed needs one_visit"),
                                          ({"time_origin": "x"}, "unknown rule time_origin")])
def test_rules_refused(raw, tmp_path, rules, match):
    with pytest.raises(LoadError, match=match):
        load(_with_rules(tmp_path, rules), raw["dummy-omop"].root, tmp_path / "out")


def test_description_is_written(loaded):
    desc = json.loads((loaded["dummy-omop"].path.parent / DESCRIPTION).read_text())
    assert desc["dataset"] == "dummy-omop" and desc["description"]["time"] == "visit-dates"
