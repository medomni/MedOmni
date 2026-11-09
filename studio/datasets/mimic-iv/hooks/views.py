"""What Build shows of a MIMIC-IV patient beyond the raw rows (evidence rules name this hook as `views`).

Why a hook: v0.2's agent-facing forms are specific to this dataset's tables. `demographics` joins two tables;
`measurements` turns the staged labs, ED vitals and OMR rows into the one long table the
`clinical-measurement-irregular` family reads; `file_meta` reads image sizes from the CXR metadata.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

VITALS = {"temperature": ("Temperature", "°F"), "heartrate": ("Heart rate", "bpm"),
          "resprate": ("Respiratory rate", "insp/min"), "o2sat": ("O2 saturation", "%"),
          "sbp": ("Systolic blood pressure", "mmHg"), "dbp": ("Diastolic blood pressure", "mmHg")}


def _table(raw_root: Path, rel: str) -> list[dict]:
    from medomni.core.loading.readers.csv_ import read_table

    return read_table(Path(raw_root) / rel)


def demographics(subjects, raw_root: Path, params: dict) -> dict[str, dict]:
    wanted = set(subjects)
    race: dict[str, str] = {}
    for r in _table(raw_root, "core/hosp/admissions.csv.gz"):  # the first row: the earliest
        if r["subject_id"] in wanted:
            race.setdefault(r["subject_id"], r.get("race"))
    out = {}
    for r in _table(raw_root, "core/hosp/patients.csv.gz"):
        s = r["subject_id"]
        if s in wanted:
            out[s] = {"sex": r.get("gender"), "anchor_age": int(r["anchor_age"]), "anchor_year": int(r["anchor_year"]),
                      "race": race.get(s)}
    return out


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float("inf") else None


@lru_cache(maxsize=None)
def _lab_names(raw_root: str) -> dict[str, str]:
    return {r["itemid"]: r["label"] for r in _table(Path(raw_root), "core/hosp/d_labitems.csv.gz")}


def measurements(tables: dict[str, list[dict]], raw_root: Path, params: dict) -> list[dict] | None:
    """One row per value, in the family's format. Built from the rows already cut, so every cut carries over."""
    labels, rows = _lab_names(str(raw_root)), []
    for r in tables.get("labevents", []):
        v = _num(r.get("valuenum"))
        if v is not None and r.get("charttime"):
            rows.append({"t": r["charttime"][:19], "measurement": labels.get(r["itemid"], f"itemid {r['itemid']}"),
                         "itemid": r["itemid"], "value": v, "unit": r.get("valueuom") or None, "_from": "labevents"})
    for r in tables.get("ed_vitalsign", []):
        for col, (name, unit) in VITALS.items():
            v = _num(r.get(col))
            if v is not None and r.get("charttime"):
                rows.append({"t": r["charttime"][:19], "measurement": name, "value": v, "unit": unit,
                             "_from": "ed_vitalsign"})
    for r in tables.get("omr", []):
        name, raw = (r.get("result_name") or "").strip(), (r.get("result_value") or "").strip()
        unit = name[name.rfind("(") + 1:-1] if name.endswith(")") and "(" in name else None
        base = name[:name.rfind("(")].strip() if unit else name
        if "/" in raw and base.lower().startswith("blood pressure"):
            sb, _, db = raw.partition("/")
            for part, v in (("systolic", _num(sb)), ("diastolic", _num(db))):
                if v is not None:
                    rows.append({"t": r["chartdate"], "measurement": f"{base} {part}", "value": v, "unit": "mmHg",
                                 "_from": "omr"})
        elif (v := _num(raw)) is not None and name:
            rows.append({"t": r["chartdate"], "measurement": base, "value": v, "unit": unit, "_from": "omr"})
    rows.sort(key=lambda x: (x["t"], x["measurement"]))
    return rows


def crop_file(rel: str, raw_root: Path, params: dict, prediction_time: str) -> bytes | None:
    """A bedside numerics table cut at the prediction time. Its first column is seconds from the record's start, which
    is in the master header. None when no row is left, or the header can't give a start: a table we can't cut is not staged."""
    import datetime as dt
    import gzip

    path = Path(raw_root) / rel
    lines = (path.parent / f"{path.parent.name}.hea").read_text().splitlines()
    head = lines[1].split() if lines and lines[0].startswith("#") else lines[0].split()
    try:
        base = dt.datetime.strptime(f"{head[5]} {head[4].split('.')[0]}", "%d/%m/%Y %H:%M:%S")
    except (IndexError, ValueError):
        return None
    cut = dt.datetime.strptime(prediction_time, "%Y-%m-%d %H:%M:%S")
    kept = []
    with gzip.open(path, "rt") as f:
        header = f.readline()
        for line in f:
            try:
                t = base + dt.timedelta(seconds=float(line.split(",", 1)[0]))
            except ValueError:
                continue
            if t <= cut:
                kept.append(line)
    return gzip.compress((header + "".join(kept)).encode(), mtime=0) if kept else None


@lru_cache(maxsize=None)
def _cxr_sizes(raw_root: str, metadata: str) -> dict[str, tuple]:
    return {r["dicom_id"]: (r["Columns"], r["Rows"]) for r in _table(Path(raw_root), metadata)}


def file_meta(rel: str, raw_root: Path, params: dict) -> dict | None:
    """A chest film's size, from the metadata table: no image is opened."""
    if not rel.endswith(".jpg"):
        return None
    size = _cxr_sizes(str(raw_root), params.get("metadata", "cxr/mimic-cxr-2.0.0-metadata.csv.gz")).get(Path(rel).stem)
    return {"width": int(size[0]), "height": int(size[1]), "frames": 1} if size else None
