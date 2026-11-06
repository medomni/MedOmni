"""The `csv` reader: tables, one event per code template a row fills (Datasets reference page)."""
from __future__ import annotations

from pathlib import Path

from . import LoadError


def read_table(path: Path) -> list[dict]:
    """Every column as text, so ids keep every digit (R-74) and empty cells stay empty."""
    import pandas as pd

    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[], compression="infer")
    return df.to_dict("records")


def read(options, root: Path, *, tables: set[str] | None = None, stats: dict | None = None) -> list[dict]:
    """Event rows from the tables (all, or only `tables`). `time` is the raw text; the loader normalises it."""
    out = []
    loaded = {}
    wanted = [n for n in options.tables if tables is None or n in tables]
    need = set(wanted) | {s.time_from.table for n, s in options.tables.items() if n in wanted and s.time_from}
    for name in need:
        spec = options.tables[name]
        loaded[name] = read_table(root / spec.file)
        if stats is not None and name in wanted:
            stats[name] = len(loaded[name])
    for name in wanted:
        spec = options.tables[name]
        lookup = None
        if spec.time_from:
            tf = spec.time_from
            src = loaded[tf.table]
            lookup = {r.get(tf.key, ""): r.get(tf.column, "") for r in src}
        for row in loaded[name]:
            subject = row.get(spec.subject, "")
            if not subject:
                raise LoadError(f"read: {spec.file}: a row has no {spec.subject}")
            base_time = row.get(spec.time, "") if spec.time else (
                lookup.get(row.get(spec.time_from.key, ""), "") if lookup is not None else "")
            for e in spec.events:
                try:
                    if any(not row.get(c, "") for c in e.columns):
                        continue  # a code column left empty: no event
                    code = e.code.format(**row)
                except KeyError as k:
                    raise LoadError(f"read: {spec.file}: no column {k} for the code {e.code}") from None
                value = None
                if e.value:
                    raw = row.get(e.value, "")
                    if raw != "":
                        try:
                            value = float(raw)
                        except ValueError:
                            raise LoadError(f"read: {spec.file}: {e.value} '{raw}' is not a number") from None
                out.append({"subject_id": subject, "time": (row.get(e.time, "") if e.time else base_time) or None,
                            "code": code, "numeric_value": value,
                            "text_value": (row.get(e.text) or None) if e.text else None,
                            "visit_id": (row.get(spec.visit) or None) if spec.visit else None,
                            "path": None, "sha256": None, "native_id": None, "_table": name})
    return out
