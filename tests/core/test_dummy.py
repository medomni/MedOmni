"""Dummy data (part 5): a conforming file for every family; dummy datasets from their dataset.yaml; planted labels."""
import csv
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from medomni.core import families, hashing
from medomni.core.families.check import conforms
from medomni.core.families.dummy import make_dummy
from medomni.core.families.dummy.datasets import INT_BASE, DummyError, Plant, make_dataset
from medomni.core.testing import DATASETS

REPO = Path(__file__).resolve().parents[2]
FAMILIES = sorted(families.load_registry(REPO))
SHAPES = ("dummy-mimic", "dummy-omop", "dummy-bdsp")


def _files(path: Path) -> list[Path]:
    return sorted(path.parent.glob(path.stem + ".*"))


@pytest.mark.parametrize("fid", FAMILIES)
def test_every_family_conforms(fid, tmp_path):
    fam = families.get(fid, REPO)
    p = make_dummy(fam, seed=1, out_dir=tmp_path)
    assert conforms(fam, p) == []
    for f in _files(p):
        assert f.stat().st_size < 1 << 20, f"{f.name} is over 1 MiB"


@pytest.mark.parametrize("fid", FAMILIES)
def test_seed_decides_the_bytes(fid, tmp_path):
    fam = families.get(fid, REPO)
    a, b, c = (make_dummy(fam, seed=s, out_dir=tmp_path / d) for s, d in ((1, "a"), (1, "b"), (2, "c")))
    assert [f.read_bytes() for f in _files(a)] == [f.read_bytes() for f in _files(b)]
    assert [f.read_bytes() for f in _files(a)] != [f.read_bytes() for f in _files(c)]


@pytest.mark.parametrize("made, checked, problem", [
    ("ecg-1lead-200hz-uv", "spo2-series-10hz-pct", "channels"),
    ("ecg-1lead-200hz-uv", "eeg-sleep-6ch-200hz-uv", "channels"),
    ("eog-2ch-200hz-uv", "resp-effort-rip-2ch-50hz", "rates"),
    ("fundus-faf-mono8-2d", "oct-volume-raster-mono8-3d", "frame"),
    ("oct-volume-raster-mono8-3d", "flio-tcspc-256x256x1024bin-u16", "bits"),
    ("wearable-hr-1min-bpm", "cgm-5min-mgdl", "body.cgm"),
    ("clinical-free-text", "clinical-measurement-irregular", "columns"),
])
def test_the_check_catches_a_wrong_file(made, checked, problem, tmp_path):
    p = make_dummy(families.get(made, REPO), seed=1, out_dir=tmp_path)
    problems = conforms(families.get(checked, REPO), p)
    assert any(problem in x for x in problems), problems


def test_the_check_catches_values_outside_the_range(tmp_path):
    import pyedflib

    fam = families.get("spo2-series-10hz-pct", REPO)
    p = tmp_path / "bad.edf"
    w = pyedflib.EdfWriter(str(p), 1, file_type=pyedflib.FILETYPE_EDF)
    w.setSignalHeaders([{"label": "spo2", "dimension": "%", "sample_frequency": 10, "physical_min": 0,
                         "physical_max": 150, "digital_min": -32768, "digital_max": 32767}])
    import numpy as np

    w.writeSamples([np.full(300, 30000, dtype=np.int32)], digital=True)
    w.close()
    assert any("outside the family's range" in x for x in conforms(fam, p))


# What to plant: the caller's (R-147). These match the labels of Studio's dummy packages (tests/studio/test_dummy_plants.py).
PLANTS = {
    "dummy-mimic": {"aki": Plant(exists="^DIAGNOSIS//ICD//N17", from_="anchor", to="anchor + 7 days"),
                    "creat_high": Plant(value="LAB//90001", op=">=", x=1.5, from_="anchor", to="anchor + 2 days")},
    "dummy-omop": {"hba1c_high": Plant(value="MEASUREMENT//hba1c", op=">=", x=6.5, from_="anchor", to="anchor + 2 days"),
                   "retinopathy": Plant(exists="^CONDITION//H35", from_="anchor", to="anchor + 30 days")},
    "dummy-bdsp": {"osa": Plant(value="AHI", op=">=", x=15, from_="any", to="any")},
}


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    out = tmp_path_factory.mktemp("datasets")
    return {s: make_dataset(DATASETS / s, out / s, plant=PLANTS[s]) for s in SHAPES}


def _codes(package: Path) -> set[str]:
    with open(package / "codes.csv", newline="", encoding="utf-8") as f:
        return {r["code"] for r in csv.DictReader(f)}


def _rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("shape", SHAPES)
def test_dataset_has_what_its_config_names(made, shape):
    from medomni.core.contracts import DatasetConfig, load
    from medomni.core.loading.options import options

    d = made[shape]
    cfg = load(DATASETS / shape / "dataset.yaml", DatasetConfig)
    known = _codes(DATASETS / shape)
    for r in cfg.read:
        o = options(r)
        if r.reader == "csv":
            for name, spec in o.tables.items():
                rows = _rows(d.root / spec.file)
                assert rows, name
                for row in rows:
                    s = row[spec.subject]
                    assert s.startswith("DUMMY-") or int(s) > INT_BASE, s
                    for e in spec.events:
                        code = e.code.format(**row)
                        assert code in known, f"{name} emits {code}, which codes.csv doesn't list"
        else:
            for entry, spec in o.files.items():
                found = sorted(d.root.glob(re.sub(r"\{[a-z]+\}", "*", spec.pattern)))
                assert len(found) == len(d.subjects) * spec.per_subject, entry
                assert all(p.stat().st_size < 1 << 20 for p in found), entry
                if spec.format == "family":
                    fam = families.get(entry, REPO)
                    assert all(conforms(fam, p) == [] for p in found), entry


@pytest.mark.parametrize("shape", SHAPES)
def test_dataset_is_reproducible(made, shape, tmp_path):
    a, b = (make_dataset(DATASETS / shape, tmp_path / d, subjects=3) for d in ("a", "b"))
    assert hashing.dir_hash(a.root) == hashing.dir_hash(b.root)
    other = make_dataset(DATASETS / shape, tmp_path / "other", subjects=3, seed=1)
    assert hashing.dir_hash(other.root) != hashing.dir_hash(a.root)


@pytest.mark.parametrize("shape", SHAPES)
def test_planted_labels_and_canaries(made, shape):
    from medomni.core.contracts import DatasetConfig, load
    from medomni.core.loading.options import options

    d = made[shape]
    assert json.loads((d.root.parent / "planted.json").read_text()) == d.planted
    labels = PLANTS[shape]
    cfg = load(DATASETS / shape / "dataset.yaml", DatasetConfig)
    tables = {n: s for r in cfg.read if r.reader == "csv" for n, s in options(r).tables.items()}
    assert set(d.planted["labels"]) == set(labels)
    for name, lab in labels.items():
        p = d.planted["labels"][name]
        assert 0 < len(p["positive"]) < len(d.subjects)
        for ev in p["events"]:
            spec = tables[ev["table"]]
            rows = [r for r in _rows(d.root / spec.file) if r[spec.subject] == ev["subject"]]
            emitted = {e.code.format(**r) for r in rows for e in spec.events}
            assert ev["code"] in emitted
            if lab.value:
                col = next(e.value for e in spec.events if e.pattern().match(ev["code"]))
                assert any(float(r[col]) == ev["value"] for r in rows)
                hit = {">=": ev["value"] >= lab.x, "<": ev["value"] < lab.x}[lab.op]
                assert hit == (ev["subject"] in p["positive"])
            if lab.from_ != "any":  # a canary: after the anchor
                assert ev["time"] > d.planted["subjects"][ev["subject"]]["anchor"]
        if lab.exists:
            assert sorted(ev["subject"] for ev in p["events"]) == sorted(p["positive"])


def test_reserved_ids_are_64_bit(made):
    """R-74: reserved ids exceed int32 (and uint32); pandas reads them back unchanged."""
    import pandas as pd

    d = made["dummy-mimic"]
    df = pd.read_csv(d.root / "hosp/patients.csv")
    assert str(df["subject_id"].dtype) == "int64"
    assert sorted(df["subject_id"]) == sorted(d.subjects) and min(d.subjects) > 2 ** 32


def test_a_new_table_needs_no_generator_change(tmp_path):
    pkg = tmp_path / "dummy-new"
    shutil.copytree(DATASETS / "dummy-mimic", pkg)
    cfg = yaml.safe_load((pkg / "dataset.yaml").read_text())
    cfg["read"][0]["options"]["tables"]["microbiologyevents"] = {
        "file": "hosp/microbiologyevents.csv", "subject": "subject_id", "subject_type": "int", "time": "charttime",
        "events": [{"code": "MICRO//{org_name}"}]}
    (pkg / "dataset.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    with open(pkg / "codes.csv", "a", encoding="utf-8") as f:
        f.write("MICRO//ecoli,Escherichia coli,microbiologyevents\n")
    d = make_dataset(pkg, tmp_path / "out")
    rows = _rows(d.root / "hosp/microbiologyevents.csv")
    assert rows and {r["org_name"] for r in rows} == {"ecoli"}


def test_a_label_that_cannot_be_planted_is_refused(tmp_path):
    pkg = tmp_path / "dummy-bad"
    shutil.copytree(DATASETS / "dummy-mimic", pkg)
    sepsis = Plant(exists="^DIAGNOSIS//ICD//A41", from_="anchor", to="anchor + 2 days")
    with pytest.raises(DummyError, match="sepsis"):
        make_dataset(pkg, tmp_path / "out", plant={"sepsis": sepsis})
