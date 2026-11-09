"""What Build shows of an AI-READI participant beyond the raw rows (evidence rules name this hook as `views`).

Why a hook: the OMOP person row becomes `demographics`, and the OMOP measurement and observation rows become the one
long table the `clinical-measurement-irregular` family reads.
"""
from __future__ import annotations

from pathlib import Path


def demographics(subjects, raw_root: Path, params: dict) -> dict[str, dict]:
    from medomni.core.loading.readers.csv_ import read_table

    wanted = set(subjects)
    out = {}
    for r in read_table(Path(raw_root) / "clinical_data/person.csv"):
        if r["person_id"] in wanted:
            out[r["person_id"]] = {"gender": r.get("gender_source_value"),
                                   "year_of_birth": int(r["year_of_birth"]) if r.get("year_of_birth") else None}
    return out


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float("inf") else None


SOURCES = (("measurement", ("measurement_datetime", "measurement_date"), "measurement_source_value"),
           ("observation", ("observation_datetime", "observation_date"), "observation_source_value"))


def measurements(tables: dict[str, list[dict]], raw_root: Path, params: dict) -> list[dict] | None:
    rows = []
    for table, when, code in SOURCES:
        for r in tables.get(table, []):
            v = _num(r.get("value_as_number"))
            txt = (r.get("value_as_string") or "").strip()
            if v is not None and txt and _num(txt) != v:
                continue  # OMOP fills value_as_number with 0 when the value is text
            ts = next((r[k][:19] for k in when if r.get(k)), None)
            name = (r.get(code) or "").split(",")[0].strip()
            if v is not None and ts and name:
                rows.append({"t": ts, "measurement": name, "value": v, "unit": r.get("unit_source_value") or None,
                             "_from": table})
    rows.sort(key=lambda x: (x["t"], x["measurement"]))
    return rows
