"""Open mHealth JSON from the family file: a header and `body.<channel>`, a list of records on the family's grid."""
from __future__ import annotations

import json
import uuid
from datetime import timedelta
from pathlib import Path

from ..check import OMH_LAYOUT
from . import rng

RECORDS = 24
MEASURE = {"cgm": "blood_glucose"}  # the record field each channel's value sits in; default: the channel name
BOUNDS = {"mg/dl": (40.0, 400.0), "bpm": (40.0, 180.0), "brpm": (8.0, 30.0), "%": (85.0, 100.0)}


def _physiology(family, ch: str, subject: str, seed: int, n: int, step_s: float, g):
    """Values from the subject model (heart rate, breathing, SpO2) or a published range (glucose)."""
    import numpy as np

    from . import ranges
    from .subject import subject as subject_model

    s = subject_model(seed, subject)
    t = np.arange(n) * step_s % 300.0  # the subject model covers a 5-minute night; wearables repeat it
    if "heart" in ch:
        return [round(float(v), 1) for v in s.hr_at(t)]
    if "resp" in ch:
        return [round(s.br + float(g.normal(0, 0.5)), 1) for _ in range(n)]
    if "spo2" in ch or "oxygen" in ch:
        return [round(float(v), 1) for v in s.spo2_at(t)]
    r = ranges.lookup("glucose" if ch == "cgm" else ch)
    if r is None:
        return None
    walk = np.cumsum(g.normal(0, 3, n))  # a slow drift, as a glucose trace drifts
    mid = (r.low + r.high) / 2
    return [round(float(np.clip(mid + w, r.low, r.high)), 1) for w in walk]


def write(family, seed: int, path: Path, *, subject: str, start, level: str = "format") -> None:
    p = family.protocol
    step = timedelta(seconds=round(1 / p.rate_hz)) if p.rate_hz else timedelta(minutes=1)
    unit = p.units or ""
    lo, hi = (p.range if p.range is not None else BOUNDS.get(unit.lower(), (0.0, 100.0)))
    g = rng(seed, family.id)
    body = {}
    layout = OMH_LAYOUT.get(family.id)
    for ch in (p.channels if isinstance(p.channels, tuple) else ("value",)):
        key, field, unit = (layout[1], layout[2], layout[3]) if layout else (ch, MEASURE.get(ch, ch.replace("-", "_")), unit)
        values = _physiology(family, ch, subject, seed, RECORDS, step.total_seconds(), g) if level == "physiology" \
            else None
        if values is None:
            values = [round(float(g.uniform(lo, hi)), 2) for _ in range(RECORDS)]
        body[key] = [{field: {"value": values[i], "unit": unit},
                      "effective_time_frame": {"date_time": (start + i * step).isoformat() + "Z"}}
                     for i in range(RECORDS)]
    doc = {"header": {"uuid": str(uuid.uuid5(uuid.NAMESPACE_OID, f"medomni-dummy/{family.id}/{subject}/{seed}")),
                      "schema_id": {"namespace": "omh", "name": layout[0] if layout else family.id, "version": "1.0"},
                      "user_id": subject},
           "body": body}
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
