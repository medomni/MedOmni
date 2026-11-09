"""Dummy datasets from a dataset package (R-71): `make_dataset(package, out)` writes a raw folder the package's own
`dataset.yaml` can load, with labels and canaries planted by the package's `labels.yaml`.

What it reads: `dataset.yaml` (the reader options name every table, column, code template and file pattern),
`codes.csv` (every code, with its source table) and `labels.yaml`. Nothing else: no dataset, no network.

- **Subjects.** String ids are `DUMMY-<n>`; integer ids start at 9,900,000,001, a range no real dataset uses (R-74).
- **Timeline.** Subject n starts at `t0` (an invented date in 2150, 37 days apart). Its anchor is `t0 + 24 hours`.
  History rows and files fall between `t0` and the anchor.
- **Labels.** For each `exists` or `value` label, about half the subjects are positive. A positive gets a row whose
  code the rule matches, inside the label's window; for a value label, negatives get a value on the other side.
  These planted rows sit after the anchor: they are the **canaries** a leakage check must keep out of an atom.
  `planted.json`, written beside the raw folder, lists every planted row.
- **Values** (part 5b): at the physiology level, a value whose code's description names a known quantity
  (creatinine, HbA1c, heart rate, age, ...) falls in its published reference range (`ranges.py`); a value label's
  negatives get a normal value. Files follow one model per subject, so a subject's signals agree.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from . import DEFAULT_LEVEL, LEVELS, START, make_dummy, ranges, rng
from .. import get as get_family
from ..check import data_format

INT_BASE = 9_900_000_000  # reserved integer ids (R-74); subject n is INT_BASE + n
VISIT_BASE = 9_910_000_000
SPACING = timedelta(days=37)
ANCHOR = timedelta(hours=24)
HISTORY_ROWS = 3
FILE_OFFSET = timedelta(hours=2)
DISCHARGE = timedelta(days=4)  # where a one-row-per-subject table puts its other time columns
_OFFSET = re.compile(r"^(anchor|anchor\.event)\s*(?:([+-])\s*(\d+(?:\.\d+)?)\s*(minutes|hours|days))?$")


class DummyError(ValueError):
    pass


@dataclass(frozen=True)
class DummyDataset:
    root: Path  # the raw folder: the data root `dataset.yaml` reads
    planted: dict  # the contents of planted.json
    subjects: tuple


def _read_package(package: Path):
    from medomni.core.contracts import DatasetConfig, LabelLibrary, load
    from medomni.core.loading.options import options

    config = load(package / "dataset.yaml", DatasetConfig)
    with open(package / "codes.csv", newline="", encoding="utf-8") as f:
        codes = list(csv.DictReader(f))
    if not codes or set(codes[0]) != {"code", "description", "source_table"}:
        raise DummyError(f"{package / 'codes.csv'}: columns must be code, description, source_table")
    labels = load(package / "labels.yaml", LabelLibrary).root if (package / "labels.yaml").is_file() else {}
    readers = [(r.reader, options(r)) for r in config.read]
    return config, codes, labels, readers


def _offset(expr: str | None, t0: datetime, default: datetime) -> datetime:
    if expr is None or expr.strip() == "any":
        return default
    m = _OFFSET.match(expr.strip())
    if not m:
        raise DummyError(f"window '{expr}': only anchor, anchor.event and their offsets can be planted")
    base = t0 if m.group(1) == "anchor.event" else t0 + ANCHOR
    if not m.group(2):
        return base
    n = float(m.group(3)) * (1 if m.group(2) == "+" else -1)
    return base + timedelta(**{m.group(4): n})


def _fmt(t: datetime, kind: str, t0: datetime) -> str | int:
    if kind == "datetime":
        return t.strftime("%Y-%m-%d %H:%M:%S")
    if kind == "visit-dates":
        return t.strftime("%Y-%m-%d")
    return int((t - t0).total_seconds())  # seconds-from-start


def _templated(spec) -> bool:
    return any(e.columns for e in spec.events)


def make_dataset(package: str | Path, out: str | Path, subjects: int = 10, seed: int = 0,
                 level: str = DEFAULT_LEVEL) -> DummyDataset:
    """Write `<out>/raw/` (the data root) and `<out>/planted.json` from a dataset package."""
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}, not '{level}'")
    package, out = Path(package), Path(out)
    config, codes, labels, readers = _read_package(package)
    tables = {n: s for kind, o in readers if kind == "csv" for n, s in o.tables.items()}
    files = {n: s for kind, o in readers if kind == "tree" for n, s in o.files.items()}
    if config.units.table not in tables:
        raise DummyError(f"units.table '{config.units.table}' is not a csv table in dataset.yaml")
    unit_spec = tables[config.units.table]
    if config.units.column != unit_spec.subject:
        raise DummyError(f"units.column '{config.units.column}' is not the subject column of {config.units.table}")
    kind = config.description.time
    g = rng(seed, "dataset", str(package.name))
    ids = [INT_BASE + n if unit_spec.subject_type == "int" else f"DUMMY-{n}" for n in range(1, subjects + 1)]
    t0s = {s: START + i * SPACING + timedelta(hours=int(g.integers(0, 12))) for i, s in enumerate(ids)}
    visits = {s: (VISIT_BASE + i + 1 if unit_spec.subject_type == "int" else f"DUMMY-V{i + 1}")
              for i, s in enumerate(ids)}
    described = {c["code"]: c["description"] for c in codes}
    by_table = {}
    for c in codes:
        by_table.setdefault(c["source_table"], []).append(c["code"])
    label_codes = [re.compile(lab.exists) for lab in labels.values() if lab.exists] + \
                  [re.compile("^" + re.escape(lab.value) + "$") for lab in labels.values() if lab.value]

    def fill(spec, event, code: str) -> dict:
        m = event.pattern().match(code)
        if not m:
            raise DummyError(f"code {code} does not fit the template {event.code}")
        return m.groupdict()

    def noise_code(name, spec, event) -> str | None:
        pool = [c for c in by_table.get(name, []) if event.pattern().match(c) and not any(r.search(c) for r in label_codes)]
        return pool[int(g.integers(0, len(pool)))] if pool else None

    keys = {}  # table -> key column a tree entry maps its path {subject} through (subject_from)
    for e, fs in files.items():
        if fs.subject_from:
            keys.setdefault(fs.subject_from.table, set()).add(fs.subject_from.key)

    def base_row(name, spec, subject, t):
        row = {spec.subject: subject}
        for col, vals in spec.where.items():
            row[col] = vals[0]  # a row the table's filter keeps
        for col in keys.get(name, ()):
            row[col] = str(subject)  # the folder name a tree entry finds this subject's files under
        if spec.visit:
            row[spec.visit] = visits[subject]
        if spec.time:
            row[spec.time] = _fmt(t, kind, t0s[subject])
        if spec.time_from:
            row[spec.time_from.key] = visits[subject]
        return row

    def normal(code: str):
        r = ranges.lookup(described.get(code, "")) if level == "physiology" else None
        return ranges.value(r, g) if r else round(float(g.uniform(1, 100)), 2)

    def event_cols(name, spec, event, row, subject, code=None, value=None):
        if event.columns:
            code = code or noise_code(name, spec, event)
            if code is None:
                return False
            row.update(fill(spec, event, code))
        if event.value:
            row[event.value] = normal(code or event.code) if value is None else value
        if event.text:
            row[event.text] = f"dummy text {int(g.integers(0, 1000))}"
        if event.time:
            row[event.time] = _fmt(t0s[subject] + DISCHARGE, kind, t0s[subject])
        for c, vals in event.equals.items():
            row[c] = vals[0]  # a row the event's condition emits
        for c in event.present:
            row.setdefault(c, _fmt(t0s[subject] + DISCHARGE, kind, t0s[subject]))
        for c in event.absent:
            row.pop(c, None)
        if event.path:
            row.update({f: f"dummy-{f}" for _, f, _, _ in __import__("string").Formatter().parse(event.path)
                        if f and f not in row})
        return True

    rows: dict[str, list[dict]] = {n: [] for n in tables}
    one_row = {n for n, s in tables.items() if not _templated(s) or (s.time is None and s.time_from is None)}
    for name, spec in tables.items():
        for subject in ids:
            t0 = t0s[subject]
            if name in one_row:
                row = base_row(name, spec, subject, t0)
                if all(event_cols(name, spec, e, row, subject) for e in spec.events):
                    rows[name].append(row)
                continue
            for _ in range(HISTORY_ROWS):
                t = t0 + timedelta(hours=int(g.integers(1, 20)))
                for e in spec.events:
                    row = base_row(name, spec, subject, t)
                    if event_cols(name, spec, e, row, subject):
                        rows[name].append(row)

    # Plant labels: positives get the rule's code inside its window (the canaries)
    planted = {"anchor": "t0 + 24 hours", "subjects": {}, "labels": {}}
    for s in ids:
        planted["subjects"][str(s)] = {"t0": _fmt(t0s[s], "datetime", t0s[s]),
                                       "anchor": _fmt(t0s[s] + ANCHOR, "datetime", t0s[s])}
    hook_only = {c["code"] for c in codes if c["source_table"].startswith("hook:")}
    for label_name, lab in labels.items():
        if not (lab.exists or lab.value):
            continue
        rule = re.compile(lab.exists) if lab.exists else re.compile("^" + re.escape(lab.value) + "$")
        table_codes = [c for n in tables for c in by_table.get(n, []) if rule.search(c)]
        if not table_codes and any(rule.search(c) for c in hook_only):
            continue  # a hook derives this code from other rows: nothing to plant
        if any(str(w or "").startswith("visit:") for w in (lab.from_, lab.to)):
            planted.setdefault("not_planted", []).append(label_name)  # a window on a visit's event: no canary
            continue
        target = next(((n, spec, e, c) for n, spec in tables.items() for e in spec.events
                       for c in by_table.get(n, []) if rule.search(c) and e.pattern().match(c)
                       and (lab.exists or e.value)), None)
        if target is None:
            raise DummyError(f"label {label_name}: no code in codes.csv fits both the rule and a table template")
        name, spec, event, code = target
        positives = sorted(ids[i] for i in g.choice(len(ids), size=max(1, len(ids) // 2), replace=False))
        if len(positives) == len(ids):
            positives = positives[:-1]
        events = []
        for subject in ids:
            pos = subject in positives
            if lab.exists and not pos:
                continue
            t0 = t0s[subject]
            lo = _offset(lab.from_, t0, t0)
            hi = _offset(lab.to, t0, t0 + ANCHOR + timedelta(days=2))
            t = lo + (hi - lo) / 2
            value = None
            if lab.value:
                x = lab.x if lab.x is not None else 1.0
                hit = {">": x * 1.5 + 1, ">=": x * 1.5 + 1, "<": x * 0.5 - 1, "<=": x * 0.5 - 1, "==": x}
                miss = {">": x * 0.5 - 1, ">=": x * 0.5 - 1, "<": x * 1.5 + 1, "<=": x * 1.5 + 1, "==": x + 1}
                value = round((hit if pos else miss)[lab.op or ">="], 3)
                r = ranges.lookup(described.get(code, "")) if level == "physiology" else None
                if not pos and r is not None:
                    v = ranges.value(r, g)  # a negative gets a normal value, when the normal range fails the rule
                    fails = {">": v <= x, ">=": v < x, "<": v >= x, "<=": v > x, "==": v != x}[lab.op or ">="]
                    value = v if fails else value
            if name in one_row:
                row = next(r for r in rows[name] if r[spec.subject] == subject)
                event_cols(name, spec, event, row, subject, code=code, value=value)
                t = t0
                if spec.time_from:
                    t = t0 + DISCHARGE
            else:
                row = base_row(name, spec, subject, t)
                event_cols(name, spec, event, row, subject, code=code, value=value)
                if spec.time_from:
                    t = t0 + DISCHARGE  # the time it takes from its source row
                rows[name].append(row)
            if not (lab.from_ in (None, "any") or lo <= t <= hi):
                raise DummyError(f"label {label_name}: table {name} puts its rows at {t}, outside the window")
            events.append({"subject": str(subject), "code": code, "table": name, "time": _fmt(t, "datetime", t0),
                           **({"value": value} if value is not None else {})})
        planted["labels"][label_name] = {"positive": [str(s) for s in positives], "events": events}

    root = out / "raw"
    by_file: dict[str, list[dict]] = {}  # tables reading one file (with different filters) share its rows
    named: dict[str, list[str]] = {}  # every column the options name, so a table with no rows still has its header
    for name, spec in tables.items():
        by_file.setdefault(spec.file, []).extend(rows[name])
        named.setdefault(spec.file, []).extend(spec.column_names())
    for file, file_rows in by_file.items():
        cols = list(dict.fromkeys([*(k for r in file_rows for k in r), *named[file]]))
        p = root / file.replace("*", "dummy")  # a glob gets one file
        p.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(file_rows, key=lambda r: tuple(str(r.get(c, "")) for c in cols))
        if p.suffix == ".parquet":
            import pyarrow as pa
            import pyarrow.parquet as pq

            pq.write_table(pa.table({c: [str(r.get(c, "")) for r in ordered] for c in cols}), p)
            continue
        opener = __import__("gzip").open if p.suffix == ".gz" else open
        with opener(p, "wt", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(ordered)

    for entry, spec in files.items():
        for i, subject in enumerate(ids):
            for k in range(spec.per_subject):
                record = f"{subject}-{k + 1}"
                rel = Path(spec.pattern.format(subject=subject, record=record))
                start = t0s[subject] + FILE_OFFSET + timedelta(hours=k)
                if spec.format == "h5":
                    from .signal import write_h5

                    (root / rel.parent).mkdir(parents=True, exist_ok=True)
                    write_h5([get_family(f) for f in spec.families], seed + i, root / rel, subject=str(subject),
                             start=start, level=level)
                    continue
                family = get_family(entry)
                written = make_dummy(family, seed + i, root / rel.parent, rel.stem, subject=str(subject), start=start,
                                     level=level)
                if written.name != rel.name:
                    raise DummyError(f"files.{entry}: pattern ends in '{rel.suffix}', a {data_format(family)} "
                                     f"file is '{written.suffix}'")
    rule = config.verify.get("version")
    if rule:  # the file the package reads the copy's version from
        vp = root / rule["file"]
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(json.dumps({rule["key"]: config.description.version}) + "\n" if "key" in rule
                      else f"{rule['contains']}\n", encoding="utf-8")
    from medomni.core.loading import hooks

    for kind, o in readers:
        if kind == "hook":
            mod = hooks.module(package, o.hook)
            if hasattr(mod, "dummy"):
                mod.dummy(root, {str(s): t0s[s] for s in ids}, dict(o.params), g)
    out.mkdir(parents=True, exist_ok=True)
    (out / "planted.json").write_text(json.dumps(planted, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return DummyDataset(root, planted, tuple(ids))
