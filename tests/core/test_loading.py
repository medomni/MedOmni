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
    assert all(e["sha256"] is None for e in files)  # the load never reads a whole recording to hash it
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


# ---- the reader options part 2 added (Stage 3)
def _package(tmp_path, tables, extra_read=(), rules=None, codes=("A", "B"), verify=None):
    p = tmp_path / "pkg"
    (p / "hooks").mkdir(parents=True, exist_ok=True)
    read = [{"reader": "csv", "options": {"tables": tables}}, *extra_read]
    cfg = {"description": {"unit": "patient", "time": "datetime", "version": "1"},
           "units": {"table": next(iter(tables)), "column": "s"}, "source": "all", "read": read}
    if rules:
        cfg["rules"] = rules
    if verify:
        cfg["verify"] = verify
    (p / "dataset.yaml").write_text(yaml.safe_dump(cfg))
    (p / "codes.csv").write_text("code,description,source_table\n" + "".join(f"{c},d,t\n" for c in codes))
    return p


def _raw(tmp_path, files):
    root = tmp_path / "raw"
    for rel, text in files.items():
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    return root


def _codes(p, root, tmp_path):
    return [(e["subject_id"], e["time"], e["code"]) for e in rows(load(p, root, tmp_path / "o").path)]


T = {"file": "t.csv", "subject": "s", "time": "t", "events": [{"code": "A"}]}


def test_where_keeps_listed_rows(tmp_path):
    p = _package(tmp_path, {"t": {**T, "where": {"k": ["1"]}}})
    root = _raw(tmp_path, {"t.csv": "s,t,k\n1,2150-01-01,1\n2,2150-01-01,2\n"})
    assert [c[0] for c in _codes(p, root, tmp_path)] == ["1"]


def test_a_glob_reads_every_file_and_parquet_as_text(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    p = _package(tmp_path, {"t": {**T, "file": "d/*.parquet"}})
    root = tmp_path / "raw"
    (root / "d").mkdir(parents=True)
    for i in (1, 2):
        pq.write_table(pa.table({"s": [i * 11], "t": ["2150-01-01"]}), root / "d" / f"{i}.parquet")
    assert sorted(c[0] for c in _codes(p, root, tmp_path)) == ["11", "22"]


def test_clean_before_remove_lower(tmp_path):
    t = {**T, "clean": {"k": {"before": ",", "remove": ".", "lower": True}}, "events": [{"code": "C//{k}"}]}
    p = _package(tmp_path, {"t": t}, codes=("C//a1",))
    root = _raw(tmp_path, {"t.csv": 's,t,k\n1,2150-01-01,"A.1, some label"\n'})
    assert _codes(p, root, tmp_path)[0][2] == "C//a1"


def test_event_conditions_and_missing_time(tmp_path):
    t = {**T, "time": "a", "events": [
        {"code": "A", "time": "d", "present": ["d"]},
        {"code": "A", "time": "e", "absent": ["d"], "equals": {"f": ["1"]}}]}
    p = _package(tmp_path, {"t": t})
    root = _raw(tmp_path, {"t.csv": "s,a,d,e,f\n1,2150-01-01,2150-01-02,2150-01-03,1\n2,2150-01-01,,2150-01-04,1\n3,2150-01-01,,2150-01-05,0\n"})
    assert sorted(c[:2] for c in _codes(p, root, tmp_path)) == [("1", "2150-01-02T00:00:00"), ("2", "2150-01-04T00:00:00")]


def test_missing_time_drop(tmp_path):
    p = _package(tmp_path, {"t": {**T, "missing_time": "drop"}})
    root = _raw(tmp_path, {"t.csv": "s,t\n1,2150-01-01\n2,\n"})
    assert [c[0] for c in _codes(p, root, tmp_path)] == ["1"]


def test_a_load_false_table_is_verified_but_not_read(tmp_path):
    p = _package(tmp_path, {"t": T, "big": {**T, "file": "big.csv", "load": False}})
    root = _raw(tmp_path, {"t.csv": "s,t\n1,2150-01-01\n"})
    with pytest.raises(LoadError, match="big.csv"):
        load(p, root, tmp_path / "o")
    (root / "big.csv").write_text("s,t\n9,2150-01-01\n")
    assert [c[0] for c in _codes(p, root, tmp_path)] == ["1"]


def test_csv_event_path_only_on_file_codes(tmp_path):
    t = {**T, "events": [{"code": "FILE//clinical-record-table", "path": "d/{s}"}]}
    p = _package(tmp_path, {"t": t})
    root = _raw(tmp_path, {"t.csv": "s,t\n7,2150-01-01\n"})
    assert rows(load(p, root, tmp_path / "o").path)[0]["path"] == "d/7"
    p = _package(tmp_path, {"t": {**T, "events": [{"code": "A", "path": "d"}]}})
    with pytest.raises(LoadError, match="FILE//<family>"):
        load(p, root, tmp_path / "o2")


def _tree(tmp_path, entry, table_rows="s,t,f\n1,2150-01-01,sub-a\n"):
    tree = {"reader": "tree", "options": {"files": {"cxr-radiograph-2d": entry}}}
    return _package(tmp_path, {"t": T}, extra_read=[tree]), _raw(tmp_path, {"t.csv": table_rows})


def test_tree_skips_dotfiles_and_excluded(tmp_path):
    p, root = _tree(tmp_path, {"pattern": "x/{subject}/{record}.png", "exclude": ["skip"]})
    for name in ("a.png", ".partial.png", "skip-me.png"):
        f = root / "x/1" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    (root / "x/1/empty.png").write_bytes(b"")
    assert [r["path"] for r in rows(load(p, root, tmp_path / "o").path) if r["path"]] == ["x/1/a.png"]


def test_tree_subject_from_maps_a_folder_to_the_subject(tmp_path):
    p, root = _tree(tmp_path, {"pattern": "x/{subject}/{record}.png", "subject_from": {"table": "t", "key": "f"}})
    for d in ("sub-a", "sub-unknown"):
        (root / "x" / d).mkdir(parents=True)
        (root / "x" / d / "a.png").write_bytes(b"x")
    files = [r for r in rows(load(p, root, tmp_path / "o").path) if r["path"]]
    assert [(r["subject_id"], r["path"]) for r in files] == [("1", "x/sub-a/a.png")]


HOOK = """\
def inputs(raw_root, params):
    return [params["file"]]
def derive(rows, raw_root, params):
    return [{"subject_id": r["subject_id"], "code": "B", "time": None} for r in rows if r["code"] == "A"]
"""


def test_a_hook_sees_earlier_rows_and_its_inputs_are_verified(tmp_path):
    p = _package(tmp_path, {"t": T}, extra_read=[{"reader": "hook", "options": {"hook": "h", "params": {"file": "in.txt"}}}])
    (p / "hooks/h.py").write_text(HOOK)
    root = _raw(tmp_path, {"t.csv": "s,t\n1,2150-01-01\n"})
    with pytest.raises(LoadError, match="in.txt"):
        load(p, root, tmp_path / "o")
    (root / "in.txt").write_text("x")
    assert sorted(c[2] for c in _codes(p, root, tmp_path)) == ["A", "B"]


def test_a_hook_row_needs_a_code_and_event_columns_only(tmp_path):
    p = _package(tmp_path, {"t": T}, extra_read=[{"reader": "hook", "options": {"hook": "h"}}])
    (p / "hooks/h.py").write_text("def derive(rows, raw_root, params):\n    return [{'subject_id': '1', 'code': 'A', 'x': 1}]\n")
    root = _raw(tmp_path, {"t.csv": "s,t\n1,2150-01-01\n"})
    with pytest.raises(LoadError, match="only event columns"):
        load(p, root, tmp_path / "o")


def test_verify_manifests(tmp_path):
    p = _package(tmp_path, {"t": T}, verify={"manifests": "*/manifest.tsv"})
    root = _raw(tmp_path, {"t.csv": "s,t\n1,2150-01-01\n", "m/manifest.tsv": "x\tdata_filepath\tother_file_path\n1\t/m/a.txt\tNot reported\n2\t/m/a.txt\tNone\n"})
    with pytest.raises(LoadError, match="manifest lists"):
        load(p, root, tmp_path / "o")
    (root / "m/a.txt").write_text("x")
    assert _codes(p, root, tmp_path)


@pytest.mark.parametrize("rule,text", [({"file": "v.json", "key": "version"}, '{"version": "1"}'),
                                       ({"file": "v.txt", "contains": "release 1", "version": "1"}, "the release 1 notes")])
def test_verify_version(tmp_path, rule, text):
    p = _package(tmp_path, {"t": T}, verify={"version": rule})
    root = _raw(tmp_path, {"t.csv": "s,t\n1,2150-01-01\n", rule["file"]: text})
    assert _codes(p, root, tmp_path)
    (root / rule["file"]).write_text('{"version": "2"}')
    with pytest.raises(LoadError, match="the package describes"):
        load(p, root, tmp_path / "o2")
