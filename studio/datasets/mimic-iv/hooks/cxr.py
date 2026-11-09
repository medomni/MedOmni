"""MIMIC-CXR index: one `CXR//STUDY` and one `FILE//cxr-radiograph-2d` row per image, from the metadata table.

Why a hook: the image time is `StudyDate` plus `StudyTime`, a number with its leading zeros dropped (93049.828 is
09:30:49), and the image path is built from the subject's first two digits. No reader option says either. The folder
walk the tree reader would do instead reads 377k files. v0.2: `buildcache._cxr` and `adapters.mimic_cxr_image`.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

COLUMNS = ["dicom_id", "subject_id", "study_id", "StudyDate", "StudyTime", "ViewPosition"]
FRONTAL = ("PA", "AP")


def _time(date: str, tm: str) -> str | None:
    if not date:
        return None
    t = datetime.strptime(date + (tm.split(".")[0] or "0").zfill(6), "%Y%m%d%H%M%S")
    return t.isoformat(timespec="seconds")


def inputs(raw_root: Path, params: dict) -> list[str]:
    return [params["metadata"]]


def derive(rows, raw_root: Path, params: dict) -> list[dict]:
    from medomni.core.loading.readers.csv_ import read_table

    out = []
    for r in read_table(raw_root / params["metadata"], columns=COLUMNS):
        s, t = r["subject_id"], _time(r["StudyDate"], r["StudyTime"])
        out.append({"subject_id": s, "time": t, "code": "CXR//STUDY", "native_id": r["dicom_id"]})
        if r["ViewPosition"] in FRONTAL:  # the family is frontal films
            out.append({"subject_id": s, "time": t, "code": "FILE//cxr-radiograph-2d", "native_id": r["dicom_id"],
                        "path": f"cxr/files/p{s[:2]}/p{s}/s{r['study_id']}/{r['dicom_id']}.jpg"})
    return out


def dummy(raw_root: Path, subjects: dict, params: dict, rng) -> None:
    """One study per subject, an hour after its t0, in the metadata table's own columns."""
    import csv
    from datetime import timedelta

    p = Path(raw_root) / params["metadata"]
    p.parent.mkdir(parents=True, exist_ok=True)
    opener = __import__("gzip").open if p.suffix == ".gz" else open
    with opener(p, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLUMNS)
        for i, (s, t0) in enumerate(sorted(subjects.items())):
            t = t0 + timedelta(hours=1)
            w.writerow([f"dummy-dicom-{i + 1}", s, 50000000 + i, t.strftime("%Y%m%d"), t.strftime("%H%M%S") + ".000", "PA"])
