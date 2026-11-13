"""The three shipped dataset packages and `bench data` on their dummy copies (R-71, R-119, R-125). No real data."""
import csv
import importlib.util
from collections import defaultdict
from pathlib import Path

import pytest

from medomni.bench import data as connect_data
from medomni.studio import data
from medomni.studio.build.labels import anchor, label
from medomni.core.contracts import load as load_contract
from medomni.studio.build.contracts import Cohort, LabelLibrary, TaskTemplate
from medomni.core.families.dummy.datasets import make_dataset
from medomni.core.loading import load

REPO = Path(__file__).resolve().parents[2]
PACKAGES = ("aireadi", "bdsp", "mimic-iv")


def package(name):
    return REPO / "studio/datasets" / name


def hook(name, module):
    spec = importlib.util.spec_from_file_location(f"t_{module}", package(name) / "hooks" / f"{module}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def copies(tmp_path_factory):
    out = tmp_path_factory.mktemp("copies")
    return {p: make_dataset(package(p), out / p, subjects=6) for p in PACKAGES}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "workspace.yaml").write_text(f"""\
datasets: {{}}
cache: {tmp_path}/cache
tasks: {tmp_path}/tasks
runs: {tmp_path}/runs
results: {tmp_path}/results.jsonl
hf_cache: {tmp_path}/hf
""")
    monkeypatch.setenv("MEDOMNI_HOME", str(tmp_path))
    return tmp_path


def _connect(name, root):
    assert connect_data.connect(name, str(root)) == 0


@pytest.mark.parametrize("name", PACKAGES)
def test_every_package_passes_data_check_on_its_dummy_copy(name, copies, workspace, capsys):
    _connect(name, copies[name].root)
    assert data.check(name) == 0, capsys.readouterr().out


@pytest.mark.parametrize("name", PACKAGES)
def test_every_target_label_computes_on_the_dummy_copy(name, copies, tmp_path):
    """Every target every template names comes out of `labels.yaml` without an error, on every dummy subject."""
    import pyarrow.parquet as pq

    r = load(package(name), copies[name].root, tmp_path / name)
    events = defaultdict(list)
    for row in pq.read_table(r.path).to_pylist():
        events[row["subject_id"]].append(row)
    lib = load_contract(package(name) / "labels.yaml", LabelLibrary).root
    pairs = 0
    for tdir in sorted((package(name) / "tasks").glob("*/")):
        tpl = load_contract(tdir / "template.yaml", TaskTemplate)
        for cp in sorted((tdir / "cohorts").glob("*.yaml")):
            co = load_contract(cp, Cohort)
            pairs += 1
            for es in events.values():
                ctx = anchor(es, co.anchor)
                for t in tpl.targets if ctx else ():
                    label(lib[t.label.split(":", 1)[1]], ctx)
    assert pairs


def _night_scores(root):
    return sorted(Path(root).rglob("*_scores.csv"))[0]


def test_an_unclassified_raw_label_is_refused(copies, workspace, tmp_path, capsys):
    import shutil

    root = tmp_path / "copy"
    shutil.copytree(copies["bdsp"].root, root)
    with open(_night_scores(root), "a") as f:
        f.write("Not A Stage\n")
    _connect("bdsp", root)
    assert data.check("bdsp") == 1
    assert "psg_stages:Not A Stage" in capsys.readouterr().out


def test_a_wrong_version_is_refused(copies, workspace, tmp_path, capsys):
    import shutil

    root = tmp_path / "copy"
    shutil.copytree(copies["aireadi"].root, root)
    (root / "dataset_description.json").write_text('{"version": "9.9"}')
    _connect("aireadi", root)
    assert data.check("aireadi") == 1
    assert "version '9.9'" in capsys.readouterr().out


def test_a_missing_file_and_column_are_named(copies, workspace, tmp_path, capsys):
    import gzip
    import shutil

    root = tmp_path / "copy"
    shutil.copytree(copies["mimic-iv"].root, root)
    (root / "core/icu/icustays.csv.gz").unlink()
    _connect("mimic-iv", root)
    assert data.check("mimic-iv") == 1
    assert "core/icu/icustays.csv.gz" in capsys.readouterr().out
    shutil.copy(copies["mimic-iv"].root / "core/icu/icustays.csv.gz", root / "core/icu/icustays.csv.gz")
    with gzip.open(root / "ed/ed/edstays.csv.gz", "wt") as f:
        f.write("subject_id,hadm_id\n1,2\n")
    assert data.check("mimic-iv") == 1
    assert "ed/ed/edstays.csv.gz: intime" in capsys.readouterr().out


def test_no_copy_connected_is_named(workspace, capsys):
    assert data.check("aireadi") == 1
    assert "data connect aireadi" in capsys.readouterr().out


def test_connect_keeps_the_file_and_replaces_an_entry(workspace, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    cfg = workspace / "workspace.yaml"
    cfg.write_text("# my note\n" + cfg.read_text())
    assert connect_data.connect("aireadi", str(a)) == 0 and connect_data.connect("aireadi", str(b)) == 0
    text = cfg.read_text()
    assert "# my note" in text and str(a) + "}" not in text and str(b) in text


def test_connect_refuses_a_relative_path(workspace, capsys):
    assert connect_data.connect("aireadi", "some/where") == 1


def test_new_writes_a_package_that_checks(tmp_path, monkeypatch, capsys):
    from medomni.core import plugins

    with monkeypatch.context() as m:
        m.setattr(plugins, "find_repo", lambda: tmp_path)
        assert data.new("my-data") == 0
        assert data.new("my-data") == 1  # refuses to overwrite
    assert data._package_problems(tmp_path / "studio/datasets/my-data") == []


# ---- hooks
def _ckd_rows(sex, age, year, creatinine):
    rows = [{"subject_id": "1", "code": f"SEX//{sex}", "numeric_value": None, "time": None},
            {"subject_id": "1", "code": "AGE", "numeric_value": age, "time": None},
            {"subject_id": "1", "code": "ANCHOR_YEAR", "numeric_value": year, "time": None}]
    return rows + [{"subject_id": "1", "code": "LAB//50912", "numeric_value": v, "time": t} for t, v in creatinine]


def _ckd(rows):
    out = hook("mimic-iv", "ckd").derive(rows, None, {"creatinine": ["LAB//50912", "LAB//52546"]})
    return {r["code"]: r for r in out}


def test_ckd_needs_two_low_values_90_days_apart():
    low = 3.0  # eGFR well under 60
    far = _ckd(_ckd_rows("F", 60, 2150, [("2150-01-01T08:00:00", low), ("2150-04-15T08:00:00", low)]))
    near = _ckd(_ckd_rows("F", 60, 2150, [("2150-01-01T08:00:00", low), ("2150-02-01T08:00:00", low)]))
    assert far["CKD//LABEL"]["numeric_value"] == 1.0 and near["CKD//LABEL"]["numeric_value"] == 0.0
    assert far["CKD//SPAN_END"]["time"] == "2150-04-15T23:59:59"


def test_ckd_every_patient_gets_a_label_and_bad_values_drop():
    got = _ckd(_ckd_rows("M", 50, 2150, [("2150-01-01T08:00:00", 0.0), ("2150-02-01T08:00:00", 60.0)]))
    assert got["CKD//LABEL"]["numeric_value"] == 0.0
    assert got["CKD//SPAN_END"]["time"] == "2150-02-01T23:59:59"  # the span counts every creatinine row


def test_ckd_egfr_is_v02s_equation():
    e = hook("mimic-iv", "ckd").egfr_ckdepi_2021(1.0, 60, True)
    assert e == pytest.approx(142.0 * (1 / 0.7) ** -1.2 * 0.9938 ** 60 * 1.012)


def test_cxr_time_restores_leading_zeros():
    assert hook("mimic-iv", "cxr")._time("21500102", "93049.828") == "2150-01-02T09:30:49"


def test_cxr_rows_and_path(tmp_path):
    p = tmp_path / "m.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dicom_id", "subject_id", "study_id", "StudyDate", "StudyTime", "ViewPosition"])
        w.writerow(["abc", "12345678", "50000001", "21500102", "120000.5", "PA"])
        w.writerow(["lat", "12345678", "50000001", "21500102", "120000.5", "LATERAL"])
    rows = hook("mimic-iv", "cxr").derive([], tmp_path, {"metadata": "m.csv"})
    assert {r["code"] for r in rows} == {"CXR//STUDY", "FILE//cxr-radiograph-2d"}
    assert len([r for r in rows if r["code"] == "CXR//STUDY"]) == 2  # every study; only frontal films are files
    assert next(r for r in rows if r["code"].startswith("FILE"))["path"] == "cxr/files/p12/p12345678/s50000001/abc.jpg"


def test_sleep_metrics_are_v02s_formulas():
    from collections import Counter

    psg = hook("bdsp", "psg")
    got = psg.metrics(Counter({"W": 20, "N2": 60, "N3": 10, "R": 10}), Counter({"Hypopnea": 8, "LM": 4, "Inspiration": 3}))
    hours = 80 * 30 / 3600
    assert got["EFFICIENCY"] == 0.8 and got["N3_FRACTION"] == 0.125 and got["REM_FRACTION"] == 0.125
    assert got["AHI"] == round(8 / hours, 2) and got["LIMB_INDEX"] == round(4 / hours, 2)


def test_unreadable_events_leave_event_metrics_out():
    from collections import Counter

    got = hook("bdsp", "psg").metrics(Counter({"W": 1, "N2": 3}), None)
    assert "AHI" not in got and "EFFICIENCY" in got


def test_no_scored_sleep_has_no_metrics():
    from collections import Counter

    assert hook("bdsp", "psg").metrics(Counter(), Counter()) == {}


def _numerics(tmp_path):
    import gzip

    rec = tmp_path / "wdb/waves/p100/p10000001/81000001"
    rec.mkdir(parents=True)
    (rec / "81000001.hea").write_text("81000001/2 1 62.47 1000 10:00:00.000 01/01/2150\n81000001_0001 1000\n")
    with gzip.open(rec / "81000001n.csv.gz", "wt") as f:
        f.write("time,HR [bpm]\n0,80\n3600,90\n7200,100\n")
    return "wdb/waves/p100/p10000001/81000001/81000001n.csv.gz"


def test_bedside_numerics_are_cut_at_the_prediction_time(tmp_path):
    import gzip

    rel = _numerics(tmp_path)
    data = hook("mimic-iv", "views").crop_file(rel, tmp_path, {}, "2150-01-01 11:00:00")
    assert gzip.decompress(data).decode().splitlines() == ["time,HR [bpm]", "0,80", "3600,90"]


def test_a_numerics_table_with_nothing_before_the_cutoff_is_not_staged(tmp_path):
    rel = _numerics(tmp_path)
    assert hook("mimic-iv", "views").crop_file(rel, tmp_path, {}, "2149-12-31 00:00:00") is None
