"""The `csv` reader: tables, one event per code template a row fills (Datasets reference page)."""
from __future__ import annotations

from pathlib import Path

from . import LoadError


CHUNK = 1_000_000  # rows per chunk when a `where` filter reads a large table


def files(spec, root: Path) -> list[Path]:
    """The table's files: one path, or every match of a glob, sorted."""
    if "*" in spec.file:
        return sorted(p for p in root.glob(spec.file) if p.is_file())
    return [root / spec.file]


def _text(df):
    """Every column as text; missing cells empty."""
    return df.astype(object).where(df.notna(), "").astype(str)


def read_table(path: Path, where: dict | None = None, columns: list[str] | None = None) -> list[dict]:
    """Every column as text, so ids keep every digit (R-74) and empty cells stay empty. Parquet files are read as
    text too. With `where`, only rows whose column holds a listed value are kept, read in chunks."""
    import pandas as pd

    path = Path(path)
    if path.suffix == ".parquet":
        df = _text(pd.read_parquet(path, columns=columns))
        for col, vals in (where or {}).items():
            df = df[df[col].isin(set(vals))]
        return df.to_dict("records")
    kw = dict(dtype=str, keep_default_na=False, na_values=[], compression="infer", usecols=columns)
    if not where:
        return pd.read_csv(path, **kw).to_dict("records")
    out = []
    for chunk in pd.read_csv(path, chunksize=CHUNK, **kw):
        for col, vals in where.items():
            chunk = chunk[chunk[col].isin(set(vals))]
        out += chunk.to_dict("records")
    return out


def columns(path: Path) -> list[str]:
    """A table file's column names, read from its header only."""
    import pandas as pd

    path = Path(path)
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        return list(pq.read_schema(path).names)
    return list(pd.read_csv(path, nrows=0, compression="infer").columns)


def table_rows(spec, root: Path) -> list[dict]:
    """The rows of one table across its files, filtered by its `where`."""
    out = []
    for p in files(spec, root):
        out += read_table(p, dict(spec.where) or None)
    return out


def read(options, root: Path, *, tables: set[str] | None = None, stats: dict | None = None) -> list[dict]:
    """Event rows from the tables (all, or only `tables`). `time` is the raw text; the loader normalises it.
    A table marked `load: false` is left out (evidence reads it), unless another table takes its time from it."""
    out = []
    loaded = {}
    wanted = [n for n, s in options.tables.items() if (tables is None or n in tables) and s.load]
    need = set(wanted) | {s.time_from.table for n, s in options.tables.items() if n in wanted and s.time_from}
    for name in need:
        spec = options.tables[name]
        loaded[name] = table_rows(spec, root)
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
            if spec.clean:
                row = {**row, **{c: cl.apply(row.get(c, "")) for c, cl in spec.clean.items()}}
            subject = row.get(spec.subject, "")
            if not subject:
                raise LoadError(f"read: {spec.file}: a row has no {spec.subject}")
            base_time = row.get(spec.time, "") if spec.time else (
                lookup.get(row.get(spec.time_from.key, ""), "") if lookup is not None else "")
            for e in spec.events:
                if not e.emits(row):
                    continue
                if spec.missing_time == "drop" and not ((row.get(e.time, "") if e.time else base_time)):
                    continue
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
                path = None
                if e.path:
                    if not code.startswith("FILE//"):
                        raise LoadError(f"read: {spec.file}: `path` is for FILE//<family> codes, not {e.code}")
                    try:
                        path = e.path.format(**row)
                    except KeyError as k:
                        raise LoadError(f"read: {spec.file}: no column {k} for the path {e.path}") from None
                out.append({"subject_id": subject, "time": (row.get(e.time, "") if e.time else base_time) or None,
                            "code": code, "numeric_value": value,
                            "text_value": (row.get(e.text) or None) if e.text else None,
                            "visit_id": (row.get(spec.visit) or None) if spec.visit else None,
                            "path": path, "sha256": None, "native_id": None, "_table": name})
    return out
