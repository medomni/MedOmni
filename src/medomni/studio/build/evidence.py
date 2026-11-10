"""What one patient's atom holds: rows, fields and files before the prediction time, minus the targets' guards.

The selector knows no dataset. It reads a package's `evidence.yaml` (S1's probe U1.22: this reproduces every v0.2 atom).
Rows are matched against the guard by the event codes they emit (R-81).
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
from pathlib import Path

from .contracts.recipe import TableRule

from .labels import Context, match

from medomni.core.tasks.times import F, _is_number, before_or_at, parse as _t  # noqa: F401


def boundary(ctx: Context) -> str | None:
    """The prediction time as text; None for a cross-sectional anchor."""
    if isinstance(ctx.anchor, dt.datetime):
        return ctx.anchor.strftime(F)
    return None if ctx.anchor is None else str(ctx.anchor)  # seconds from the start


# ---- the raw rows of the tables evidence names
def _open(path: Path):
    return gzip.open(path, "rt", newline="") if path.suffix == ".gz" else open(path, newline="")


def _csv_rows(path: Path, column: str, subjects: set[str]) -> tuple[list[str], dict[str, list[list[str]]]]:
    out: dict[str, list[list[str]]] = {}
    with _open(path) as f:
        reader = csv.reader(f)
        head = next(reader)
        i = head.index(column)
        for row in reader:
            if row[i] in subjects:
                out.setdefault(row[i], []).append(row)
    return head, out


def _parquet_rows(path: Path, column: str, subjects: set[str]) -> tuple[list[str], dict[str, list[list[str]]]]:
    import pandas as pd

    df = pd.read_parquet(path)
    head = list(df.columns)
    df[column] = df[column].astype(str)
    df = df[df[column].isin(subjects)]
    out: dict[str, list[list[str]]] = {}
    for s, g in df.groupby(column, sort=False):
        out[str(s)] = list(csv.reader(io.StringIO(g.to_csv(index=False, header=False))))
    return head, out


def read_tables(package_options: dict, wanted: list[str], raw_root: Path, subjects: set[str]):
    """{table: (head, {subject: rows})} for the tables evidence names."""
    from medomni.core.loading.readers import csv_

    tables = {}
    for name in wanted:
        spec = package_options[name]
        head, rows = None, {}
        for p in csv_.files(spec, raw_root):
            h, part = (_parquet_rows if p.suffix == ".parquet" else _csv_rows)(p, spec.subject, subjects)
            head = head or h
            for s, r in part.items():
                rows.setdefault(s, []).extend(r)
        if head is not None:
            tables[name] = (head, rows)
    return tables


# ---- the guard
def emitted_codes(spec, row: dict) -> list[str]:
    cleaned = dict(row)
    for col, how in spec.clean.items():
        if col in cleaned:
            cleaned[col] = how.apply(cleaned[col])
    return [e.code.format(**cleaned) for e in spec.events if e.emits(cleaned)]


def guard_of(pair, extra_codes=()) -> tuple[list[str], set[str]]:
    """The codes and fields of every target's guard."""
    codes, fields = list(extra_codes), set()
    for t in pair.template.targets:
        g = pair.rule(t.label).guard
        codes += g.codes
        fields |= set(g.fields)
    return codes, fields


def drops(spec, row_dict: dict, codes: list[str]) -> bool:
    return any(match(c, p) for c in emitted_codes(spec, row_dict) for p in codes)


def _fields(ref, guard_fields: set[str]):
    return guard_fields if ref == "guard.fields" else set(ref)


def select(rules: dict[str, TableRule], specs: dict, tables: dict, subject: str, b: str | None, index_visit,
           codes: list[str], guard_fields: set[str]) -> dict:
    """{table: (head, kept rows)} for one patient, in the rules' order. Same operations as U1.22's selector."""
    kept, orig = {}, {}
    for name, rule in rules.items():
        if name not in tables:
            continue
        head, per = tables[name]
        rows = per.get(subject)
        if rows is None:
            if rule.write_empty:
                kept[name] = (head, [])
            continue
        i = {c: k for k, c in enumerate(head)}
        out, src = [], []
        for r in rows:
            if rule.time and not before_or_at(r[i[rule.time]] if rule.time in i else "", b):
                continue
            if rule.time_from and b:
                tf = rule.time_from
                ph, prow = orig.get(tf.table, ([tf.key, tf.column], []))
                pi = {c: k for k, c in enumerate(ph)}
                t = {p[pi[tf.key]]: p[pi[tf.column]] for p in prow}.get(r[i[tf.key]])
                if not t and rule.missing_time == "drop":
                    continue
                if t and not before_or_at(t, b):
                    continue
            if rule.skip_index_visit and index_visit is not None and r[i[rule.visit]] == index_visit:
                continue
            if rule.drop == "guard" and codes and drops(specs[name], dict(zip(head, r)), codes):
                continue
            if rule.keep_if_kept:
                kk = rule.keep_if_kept
                ph, prow = orig.get(kk.table, ([kk.key], []))
                if r[i[kk.key]] not in {p[ph.index(kk.key)] for p in prow}:
                    continue
            src.append(r)
            r = list(r)
            if rule.end and b:
                end = r[i[rule.end]] if rule.end in i else ""
                if (not end and rule.missing_end == "after") or (end and not before_or_at(end, b)):
                    for f in rule.blank_after_end:
                        if f in i:
                            r[i[f]] = ""
            if rule.blank_in_index_visit and index_visit is not None and r[i[rule.visit]] == index_visit:
                for f in _fields(rule.blank_in_index_visit, guard_fields):
                    if f in i:
                        r[i[f]] = ""
            out.append(r)
        kept[name], orig[name] = (head, out), (head, src)
    return kept


def static_facts(rules, facts: dict, guard_fields: set[str]) -> dict:
    facts = dict(facts)
    for col in _fields(rules.static.blank, guard_fields):
        for k in (lambda a: (a,) if isinstance(a, str) else a)(rules.static.aliases.get(col, col)):
            if k in facts:
                facts[k] = ""
    return dict(sorted(facts.items()))


def file_rows(events, b: str | None) -> list[dict]:
    """The patient's raw files known by the prediction time, directories and table families left out."""
    out = []
    for e in sorted(events, key=lambda e: (e["code"], e["path"] or "")):
        if not e["code"].startswith("FILE//") or not e["path"] or not Path(e["path"]).suffix:
            continue
        t = "" if e["time"] is None else str(e["time"]).replace("T", " ")[:19]
        if before_or_at(t, b):
            out.append({"family": e["code"][6:], "path": e["path"], "t_start": t if b else ""})  # no cut: no time to show
    return out
