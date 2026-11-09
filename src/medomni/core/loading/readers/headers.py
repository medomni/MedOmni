"""A family file's start time and native id, read from its header (EDF, WFDB, DICOM, Open mHealth, h5)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def _edf(path: Path):
    import pyedflib

    r = pyedflib.EdfReader(str(path))
    try:
        return r.getStartdatetime(), None
    finally:
        r.close()


def _wfdb(path: Path):
    import wfdb

    h = wfdb.rdheader(str(path.with_suffix("")))
    t = datetime.combine(h.base_date, h.base_time) if h.base_date and h.base_time else None
    return t, h.record_name


def _dicom(path: Path):
    import pydicom

    ds = pydicom.dcmread(str(path), stop_before_pixels=True)
    raw = str(getattr(ds, "AcquisitionDateTime", "") or (getattr(ds, "StudyDate", "") + getattr(ds, "StudyTime", "")))
    t = datetime.strptime(raw[:14], "%Y%m%d%H%M%S") if len(raw) >= 14 else (
        datetime.strptime(raw[:8], "%Y%m%d") if len(raw) >= 8 else None)
    return t, str(getattr(ds, "SOPInstanceUID", "")) or None


def _json(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, dict) and isinstance(doc.get("body"), dict):  # Open mHealth: the first record's time
        for records in doc["body"].values():
            if isinstance(records, list) and records:
                when = records[0].get("effective_time_frame", {}).get("date_time")
                if when:
                    return datetime.fromisoformat(when.replace("Z", "+00:00")).replace(tzinfo=None), None
    if isinstance(doc, dict) and (doc.get("files") or doc.get("file")):  # a manifest: its first data file's time
        first = (doc.get("files") or [doc["file"]])[0]
        return start(path.parent / first)
    return None, None


def _h5(path: Path):
    import h5py

    with h5py.File(path, "r") as f:
        raw = f.attrs.get("meas_date")
    raw = raw.decode() if isinstance(raw, bytes) else raw
    return (datetime.strptime(str(raw)[:19], "%Y-%m-%d %H:%M:%S") if raw else None), None


READ = {".edf": _edf, ".hea": _wfdb, ".dcm": _dicom, ".json": _json, ".h5": _h5}


def start(path: Path) -> tuple[datetime | None, str | None]:
    """(start time, native id) of a file; (None, None) for files with no time in them (PNG, CSV)."""
    reader = READ.get(path.suffix.lower())
    return reader(path) if reader else (None, None)


def file_hash(path: Path) -> str:
    """A cheap identity of a family file for the cache key: `hashing.quick_sha`, so a load never reads a whole recording
    only to fingerprint it. A WFDB record covers its header and signal files; a manifest covers it and the files it
    lists. Length-prefixed, as `hashing.dir_hash`."""
    import hashlib

    from medomni.core import hashing

    parts = [path]
    if path.suffix.lower() == ".hea":
        parts = sorted(p for p in path.parent.glob(path.stem + ".*") if p.is_file())
    elif path.suffix.lower() == ".json":
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            doc = None
        if isinstance(doc, dict) and (doc.get("files") or doc.get("file")):
            parts = [path] + [path.parent / n for n in (doc.get("files") or [doc["file"]])]
    if len(parts) == 1:
        return hashing.quick_id(parts[0])
    h = hashlib.sha256()
    for p in parts:
        h.update(p.name.encode() + b"\0" + str(p.stat().st_size).encode() + b"\0")
        h.update(hashing.quick_id(p).encode())
    return h.hexdigest()
