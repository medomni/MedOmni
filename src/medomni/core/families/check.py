"""Does a file conform to its family? `conforms(family, path)` returns the problems, an empty list when it does.

It reads the file the way its format is read (EDF and WFDB headers and samples, DICOM and PNG headers and pixels,
Open mHealth JSON, CSV tables) and checks what the family declares: channels or roles, rate, units, dtype, range,
number of dimensions and planes. A key the family leaves null is not checked.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

# Units that name no single unit, so nothing is checked
UNCHECKED_UNITS = {None, "per-channel", "per-transducer", "per-member", "mixed", "pixel-intensity"}
RATE_TOLERANCE = 1e-3  # relative
TABLE_COLUMNS = {
    "clinical-free-text": ("subject_id", "time", "text"),
    "clinical-measurement-irregular": ("subject_id", "time", "name", "value", "unit"),
    "clinical-record-table": ("subject_id", "time", "field", "value"),
    "numeric-observation": ("subject_id", "time", "name", "value", "unit"),
}


def data_format(family) -> str:
    """The format a family's data file has: the first declared format that is not a manifest."""
    return next(f for f in family.protocol.format if f != "json-manifest")


def _norm_unit(u: str) -> str:
    return u.strip().replace("µ", "u").replace("μ", "u").lower()


def _labels(family, labels: list[str], problems: list[str]) -> None:
    p = family.protocol
    got = [x.strip().lower() for x in labels]
    if isinstance(p.channels, tuple):
        want = [c.lower() for c in p.channels]
        if sorted(got) != sorted(want):
            problems.append(f"channels {got} differ from the family's {want}")
    elif isinstance(p.channels, int):
        if len(got) != p.channels:
            problems.append(f"{len(got)} channels, the family declares {p.channels}")
    elif p.roles:
        want = {r.lower() for r in p.roles}
        if not got or not set(got) <= want:
            problems.append(f"channels {got} are not among the family's roles {sorted(want)}")


def _rate(family, rates: list[float], problems: list[str]) -> None:
    want = family.protocol.rate_hz
    if want is None:
        return
    bad = sorted({r for r in rates if abs(r - want) > RATE_TOLERANCE * want})
    if bad:
        problems.append(f"rates {bad} Hz differ from the family's {want} Hz")


def _units(family, units: list[str], problems: list[str]) -> None:
    want = family.protocol.units
    if want in UNCHECKED_UNITS:
        return
    bad = sorted({u for u in units if _norm_unit(u) != _norm_unit(want)})
    if bad:
        problems.append(f"units {bad} differ from the family's '{want}'")


def _range(family, lo: float, hi: float, problems: list[str]) -> None:
    r = family.protocol.range
    if r is not None and (lo < r[0] or hi > r[1]):
        problems.append(f"values span [{lo:g}, {hi:g}], outside the family's range [{r[0]:g}, {r[1]:g}]")


def _edf(family, path: Path, problems: list[str]) -> None:
    import numpy as np
    import pyedflib

    r = pyedflib.EdfReader(str(path))
    try:
        n = r.signals_in_file
        _labels(family, r.getSignalLabels(), problems)
        _rate(family, [r.getSampleFrequency(i) for i in range(n)], problems)
        _units(family, [r.getPhysicalDimension(i) for i in range(n)], problems)
        if n:
            values = [r.readSignal(i) for i in range(n)]
            _range(family, float(min(np.min(v) for v in values)), float(max(np.max(v) for v in values)), problems)
    finally:
        r.close()
    if family.protocol.dtype != "int16":
        problems.append(f"EDF stores int16, the family declares {family.protocol.dtype}")


def _wfdb(family, path: Path, problems: list[str]) -> None:
    import numpy as np
    import wfdb

    rec = wfdb.rdrecord(str(path.with_suffix("")))
    _labels(family, list(rec.sig_name), problems)
    _rate(family, [float(rec.fs)], problems)
    _units(family, list(rec.units), problems)
    if rec.p_signal is not None and rec.p_signal.size:
        _range(family, float(np.nanmin(rec.p_signal)), float(np.nanmax(rec.p_signal)), problems)
    if family.protocol.dtype == "int16" and set(rec.fmt) - {"16"}:
        problems.append(f"WFDB formats {sorted(set(rec.fmt))}, the family declares int16 (format 16)")


DICOM_BITS = {"uint8": 8, "uint16": 16, "float32": 32}


def _dicom(family, path: Path, problems: list[str]) -> None:
    import pydicom

    ds = pydicom.dcmread(str(path))
    p = family.protocol
    frames = int(getattr(ds, "NumberOfFrames", 1) or 1)
    planes = int(ds.SamplesPerPixel)
    if p.ndim == 2 and frames != 1:
        problems.append(f"{frames} frames, a 2-D family has one")
    if p.ndim in (3, 4) and frames < 2:
        problems.append(f"{frames} frame, a {p.ndim}-D family has several")
    want_planes = p.planes if p.planes is not None else (3 if p.ndim == 4 else None)
    if want_planes is not None and planes != want_planes:
        problems.append(f"{planes} samples per pixel, the family declares {want_planes} planes")
    if p.dtype in DICOM_BITS and int(ds.BitsAllocated) != DICOM_BITS[p.dtype]:
        problems.append(f"{ds.BitsAllocated} bits allocated, the family declares {p.dtype}")
    if p.dtype == "float32" and "FloatPixelData" not in ds:
        problems.append("no Float Pixel Data, the family declares float32")
    try:
        arr = ds.pixel_array
    except Exception as e:  # noqa: BLE001 - any decoding failure is a conformance problem
        problems.append(f"pixels do not decode: {type(e).__name__}: {e}")
        return
    if str(arr.dtype) != p.dtype and p.dtype in DICOM_BITS:
        problems.append(f"pixels decode as {arr.dtype}, the family declares {p.dtype}")


def _image(family, path: Path, problems: list[str]) -> None:
    from PIL import Image

    with Image.open(path) as im:
        mode = im.mode
    planes = {"L": 1, "RGB": 3}.get(mode)
    if planes is None:
        problems.append(f"image mode {mode}; 8-bit grey (L) or RGB expected")
    elif family.protocol.planes is not None and planes != family.protocol.planes:
        problems.append(f"{planes} planes, the family declares {family.protocol.planes}")


def _omh(family, path: Path, problems: list[str]) -> None:
    p = family.protocol
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or "header" not in doc or "body" not in doc:
        problems.append("not an Open mHealth document (header and body)")
        return
    channels = list(p.channels) if isinstance(p.channels, tuple) else list(doc["body"])
    for ch in channels:
        records = doc["body"].get(ch)
        if not isinstance(records, list) or not records:
            problems.append(f"body.{ch} is not a non-empty list of records")
            continue
        values, units, times = [], [], []
        for rec in records:
            measure = next((v for k, v in rec.items() if k != "effective_time_frame" and isinstance(v, dict)), None)
            if not measure or not isinstance(measure.get("value"), (int, float)):
                problems.append(f"body.{ch}: a record has no numeric value")
                return
            values.append(float(measure["value"]))
            units.append(str(measure.get("unit", "")))
            times.append(datetime.fromisoformat(rec["effective_time_frame"]["date_time"]))
        _units(family, units, problems)
        _range(family, min(values), max(values), problems)
        if p.rate_hz:
            step = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
            want = 1 / p.rate_hz
            if any(abs(s - want) > 0.1 * want for s in step):
                problems.append(f"body.{ch}: records are not {want:g} s apart")


def _table(family, path: Path, problems: list[str]) -> None:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        problems.append("the table has no rows")
        return
    cols = tuple(rows[0])
    want = TABLE_COLUMNS.get(family.id)
    if want is not None and cols != want:
        problems.append(f"columns {list(cols)} differ from {list(want)}")
    if family.protocol.ndim == 2 and len(cols) < 2:
        problems.append("a 2-D table has at least two columns")
    if family.protocol.dtype == "float64" and "value" in cols:
        try:
            [float(r["value"]) for r in rows]
        except ValueError:
            problems.append("value column is not numeric")
    if family.protocol.dtype == "text" and not all(r.get("text", "").strip() for r in rows):
        problems.append("a text row is empty")


CHECKS = {"edf": _edf, "wfdb": _wfdb, "dicom": _dicom, "image": _image, "omh": _omh, "table": _table}


def conforms(family, path: str | Path) -> list[str]:
    """Problems with `path` as a file of `family` (a FamilyFile); empty when it conforms."""
    path = Path(path)
    problems: list[str] = []
    try:
        CHECKS[data_format(family)](family, path, problems)
    except Exception as e:  # noqa: BLE001 - an unreadable file is a conformance problem, not a crash
        problems.append(f"cannot read as {data_format(family)}: {type(e).__name__}: {e}")
    return problems
