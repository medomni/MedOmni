"""What Build shows of a VitalDB case beyond the raw rows (evidence rules name this hook as `views`).

Why a hook: the case table's columns are demographics except the ones only known after surgery, and the lab rows become
the long table the `clinical-measurement-irregular` family reads, with ISO times counted from a fixed case start. `dummy_unit` writes a `.vital` file for dummy data.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

CASE_START = datetime(2000, 1, 1)  # the lab table's times as dates from a fixed case start, as the family needs ISO times;
# the EDF recordings start at the same moment
HIDDEN = {"subjectid", "casestart", "caseend", "dis", "death_inhosp", "icu_days", "los_postop", "los_icu"}


def demographics(subjects, raw_root: Path, params: dict) -> dict[str, dict]:
    from medomni.core.loading.readers.csv_ import read_table

    wanted = set(subjects)
    return {r["caseid"]: {k: v for k, v in r.items() if k not in HIDDEN and k != "caseid"}
            for r in read_table(Path(raw_root) / "clinical_info.csv") if r["caseid"] in wanted}


def measurements(tables: dict[str, list[dict]], raw_root: Path, params: dict) -> list[dict]:
    rows = []
    for r in tables.get("labs", []):
        try:
            v = float(r["result"])
        except (TypeError, ValueError):
            continue
        try:
            t = CASE_START + timedelta(seconds=float(r["dt"]))
        except (TypeError, ValueError):
            continue
        rows.append({"t": t.isoformat(sep=" ", timespec="seconds"), "measurement": r["name"], "value": v, "unit": None, "_from": "labs"})
    rows.sort(key=lambda x: (x["t"], x["measurement"]))
    return rows


def dummy_unit(path: Path, rng) -> None:
    from medomni.core.loading.hooks import file_module

    file_module(Path(__file__).resolve().parent.parent, "converters/vital_to_wfdb.py", "converter").write_dummy(path, 6, rng)
