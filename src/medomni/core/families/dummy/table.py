"""Tables and text from the family file (columns from `families.check.TABLE_COLUMNS`)."""
from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path

import json

from ..check import JSON_TABLES, TABLE_COLUMNS
from . import rng

ROWS = 12
NAMES = ("heart_rate", "resp_rate", "temperature", "sbp")
UNITS = {"heart_rate": "bpm", "resp_rate": "insp/min", "temperature": "C", "sbp": "mmHg"}


def write(family, seed: int, path: Path, *, subject: str, start, level: str = "format") -> None:
    from . import ranges

    cols = TABLE_COLUMNS.get(family.id, ("subject_id", "time", "field", "value"))
    g = rng(seed, family.id)
    rows = []
    for i in range(ROWS):
        t = (start + timedelta(minutes=int(g.integers(5, 90)) * (i + 1))).isoformat(sep=" ")
        name = NAMES[i % len(NAMES)]
        row = {"subject_id": subject, "time": t, "name": name, "field": f"field_{i % 4}", "unit": UNITS[name],
               "value": round(float(g.uniform(1, 200)), 2), "text": f"Dummy note {i + 1}. Generated text, no findings."}
        r = ranges.lookup(name) if level == "physiology" else None
        if r is not None:
            row["value"] = ranges.value(r, g)
        rows.append({c: row[c] for c in cols})
    if family.id in JSON_TABLES:
        path.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
