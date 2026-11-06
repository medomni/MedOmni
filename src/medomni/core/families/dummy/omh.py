"""Open mHealth JSON from the family file: a header and `body.<channel>`, a list of records on the family's grid."""
from __future__ import annotations

import json
import uuid
from datetime import timedelta
from pathlib import Path

from . import rng

RECORDS = 24
MEASURE = {"cgm": "blood_glucose"}  # the record field each channel's value sits in; default: the channel name
BOUNDS = {"mg/dl": (40.0, 400.0), "bpm": (40.0, 180.0), "brpm": (8.0, 30.0), "%": (85.0, 100.0)}


def write(family, seed: int, path: Path, *, subject: str, start) -> None:
    p = family.protocol
    step = timedelta(seconds=round(1 / p.rate_hz)) if p.rate_hz else timedelta(minutes=1)
    unit = p.units or ""
    lo, hi = (p.range if p.range is not None else BOUNDS.get(unit.lower(), (0.0, 100.0)))
    g = rng(seed, family.id)
    body = {}
    for ch in (p.channels if isinstance(p.channels, tuple) else ("value",)):
        field = MEASURE.get(ch, ch.replace("-", "_"))
        body[ch] = [{field: {"value": round(float(g.uniform(lo, hi)), 2), "unit": unit},
                     "effective_time_frame": {"date_time": (start + i * step).isoformat()}} for i in range(RECORDS)]
    doc = {"header": {"uuid": str(uuid.uuid5(uuid.NAMESPACE_OID, f"medomni-dummy/{family.id}/{subject}/{seed}")),
                      "schema_id": {"namespace": "omh", "name": family.id, "version": "1.0"},
                      "user_id": subject},
           "body": body}
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
