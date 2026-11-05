"""v0.2 family files (`data_task/families/*.yaml`) -> v0.3 family files (`core/families/<id>.yaml`).

- `reader` becomes `read_by` (R-51); `protocol.unit` becomes `units`; `protocol.valid_range` becomes `range` (R-59).
- `protocol.dtype` is kept where stated (spelled as numpy names), else derived from the first data format (R-56).
- `protocol.range` is kept where stated, and set to [0, 100] for percentages; otherwise null (unchecked).
- The optional protocol keys and the `retired` / `pending` / `omh_record` blocks are kept as they are (R-59).
"""
from __future__ import annotations

from pathlib import Path

import yaml

SOURCE = "data_task/families"
DEST = "core/families"

DTYPE_SPELLING = {"u8": "uint8", "u16": "uint16", "f32": "float32", "f64": "float64", "i16": "int16", "text": "text"}
# dtype by first declared format, for families that don't state one (U2.2): EDF and WFDB store int16 samples
DTYPE_BY_FORMAT = {"edf": "int16", "wfdb": "int16", "omh": "float64", "dicom": "uint8", "image": "uint8"}
PERCENT = {"%", "pct", "percent"}
# Tables whose columns are all numeric: the numerics table holds charted values only
NUMERIC_TABLES = {"numeric-observation"}

ORDER = ("id", "read_by", "protocol", "status", "samples", "retired", "pending", "omh_record")
PROTOCOL_ORDER = ("format", "channels", "roles", "rate_hz", "units", "ndim", "dtype", "range")


def derive_dtype(fid: str, protocol: dict) -> tuple[str, str]:
    """(dtype, where it came from)."""
    if protocol.get("dtype"):
        return DTYPE_SPELLING[protocol["dtype"]], "stated"
    fmt = next(f for f in protocol["format"] if f != "json-manifest")  # a manifest points at the data files
    if fmt == "table" and fid in NUMERIC_TABLES:
        return "float64", "numeric table"
    if fmt == "table":
        return ("text", "table of text") if "text" in fid else ("mixed", "table of mixed columns")
    return DTYPE_BY_FORMAT[fmt], f"format {fmt}"


def convert_one(src: dict) -> tuple[dict, dict]:
    """(v0.3 family data, notes on what was derived)."""
    d = dict(src)
    d["read_by"] = d.pop("reader")
    p = dict(d["protocol"])
    if "unit" in p:
        if "units" in p:
            raise ValueError(f"{d['id']}: both unit and units")
        p["units"] = p.pop("unit")
    rng = p.pop("valid_range", None)
    dtype, dtype_from = derive_dtype(d["id"], p)
    p["dtype"] = dtype
    range_from = "none"
    if rng is not None:
        p["range"], range_from = [float(rng[0]), float(rng[1])], "stated"
    elif isinstance(p.get("units"), str) and p["units"].strip().lower() in PERCENT:
        p["range"], range_from = [0.0, 100.0], "percent"
    else:
        p["range"] = None
    d["protocol"] = {k: p[k] for k in PROTOCOL_ORDER if k in p} | {k: v for k, v in p.items() if k not in PROTOCOL_ORDER}
    out = {k: d[k] for k in ORDER if k in d} | {k: v for k, v in d.items() if k not in ORDER}
    return out, {"dtype": dtype_from, "range": range_from}


def convert(repo: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    outputs, notes = {}, {}
    for path in sorted((Path(repo) / SOURCE).glob("*.yaml")):
        src = yaml.safe_load(path.read_text(encoding="utf-8"))
        data, note = convert_one(src)
        outputs[f"{DEST}/{data['id']}.yaml"] = data
        notes[data["id"]] = note
    return outputs, notes
