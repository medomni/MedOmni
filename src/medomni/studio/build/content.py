"""The content step: once per pair, whatever the arms (R-107, as amended by R-111).

    atomtasks/_content/<template>@<cohort>/
        content.json     the atom list, targets, prediction times, pool statistics, step counts
        answers.csv      each patient's answer for every target; no render ever copies it
        <atom>/record.json   the patient's evidence: tables, demographics, measurements, files
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from . import evidence as ev
from .pool import Pool

METRIC_KIND = {"auc": "auc", "qwk": "qwk", "mae": "mae"}


def table_specs(pair) -> dict:
    from medomni.core.loading.options import options

    out = {}
    for r in pair.config.read:
        if r.reader == "csv":
            out.update(options(r).tables)
    return out


def views(pair):
    """The package's views hook and its params, or (None, {})."""
    from medomni.core.loading import hooks
    from medomni.core.loading.options import options

    name = pair.evidence.views
    if name is None:
        return None, {}
    params = next((dict(options(r).params) for r in pair.config.read if r.reader == "hook" and options(r).hook == name), {})
    return hooks.module(pair.package, name, derives=False), params


def atom_name(pair, subject: str) -> str:
    return f"{pair.template.template_id}__{subject}__{pair.cohort_name}"


def pool_stats(result: Pool) -> dict:
    """Answer counts per target over the pool (the constant-answer check reads these)."""
    out = {}
    for t in result.pair.template.targets:
        counts: dict[str, int] = {}
        for p in result.patients.values():
            v = p.answers[t.name]
            if v is not None:
                counts[str(v)] = counts.get(str(v), 0) + 1
        out[t.name] = {"metric": t.metric, "n": sum(counts.values()), "counts": dict(sorted(counts.items()))}
    return out


def records(result: Pool, drawn: list[str], raw_root: Path, tables: dict) -> dict[str, dict]:
    """{subject: record} for the drawn patients; `tables` from `evidence.read_tables` (read once per dataset)."""
    pair = result.pair
    specs, rules = table_specs(pair), pair.evidence.tables
    codes, guard_fields = ev.guard_of(pair)
    hook, params = views(pair)
    facts = hook.demographics(drawn, raw_root, params) if hook is not None and hasattr(hook, "demographics") else {}
    out = {}
    for s in drawn:
        p = result.patients[s]
        b = ev.boundary(p.ctx)
        kept = ev.select(rules, specs, tables, s, b, p.ctx.visit, codes, guard_fields)
        demo = ev.static_facts(pair.evidence, facts.get(s, {}), guard_fields)
        measurements = None
        if hook is not None and hasattr(hook, "measurements"):
            measurements = hook.measurements({n: [dict(zip(h, r)) for r in rows] for n, (h, rows) in kept.items()},
                                             raw_root, params)
        out[s] = {"subject": s, "prediction_time": b, "index_visit": p.ctx.visit, "demographics": demo,
                  "tables": {n: {"head": h, "rows": rows} for n, (h, rows) in kept.items()},
                  "measurements": measurements, "files": ev.file_rows(p.ctx.events, b)}
    return out


def write(result: Pool, drawn: list[str], recs: dict[str, dict], out: Path) -> Path:
    """Write the content tree; returns its folder."""
    pair = result.pair
    root = out / pair.id
    root.mkdir(parents=True, exist_ok=True)
    (root / "content.json").write_text(json.dumps({
        "pair": pair.id, "template": pair.template.template_id, "cohort": pair.cohort_name,
        "version": pair.cohort.version, "dataset": pair.dataset, "datasets": [pair.dataset],
        "targets": [t.model_dump(mode="json", exclude_none=True) for t in pair.template.targets],
        "atoms": [{"atom": atom_name(pair, s), "subject": s, "prediction_time": recs[s]["prediction_time"]} for s in drawn],
        "pool_stats": pool_stats(result), "counts": result.counts}, indent=1) + "\n", encoding="utf-8")
    with open(root / "answers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subject_id", "target", "value", "metric"])
        for t in pair.template.targets:
            for s in drawn:
                v = result.patients[s].answers[t.name]
                w.writerow([s, t.name, "" if v is None else v, t.metric])
    for s in drawn:
        d = root / atom_name(pair, s)
        d.mkdir(exist_ok=True)
        (d / "record.json").write_text(json.dumps(recs[s]) + "\n", encoding="utf-8")
    return root
