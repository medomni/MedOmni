"""The v1 builder's refusals (R-119, R-121, R-125, R-143 a): the checks that read the recipe or the source data. Build
refuses a task that fails one, and `studio task check` runs them. The checks over built output alone are Core's
(`medomni.core.tasks.checks`). Each returns a list of problems naming the check and the target, never a patient's values.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from . import evidence as ev
from .labels import when, window
from .pool import MIN_PER_CLASS, Pool, meets, _event_requirements


# ---- content checks
def leak(pair, records: dict, specs: dict) -> list[str]:
    """No answer in the evidence: no guarded code or field, nothing from the index visit that is only known later."""
    codes, fields = ev.guard_of(pair)
    out = []
    for s, rec in records.items():
        for name, t in rec["tables"].items():
            rule = pair.evidence.tables.get(name)
            if rule is None:
                continue
            i = {c: k for k, c in enumerate(t["head"])}
            visit = rec["index_visit"]
            for r in t["rows"]:
                in_index = visit is not None and rule.visit in i and r[i[rule.visit]] == visit
                if rule.skip_index_visit and in_index:
                    out.append(f"no answer in the evidence: {s}: table {name} holds a row of the index visit")
                if rule.blank_in_index_visit and in_index:
                    held = [f for f in ev._fields(rule.blank_in_index_visit, fields) if f in i and r[i[f]].strip()]
                    if held:
                        out.append(f"no answer in the evidence: {s}: table {name} index row holds {sorted(held)}")
                if rule.drop == "guard" and codes and name in specs and ev.drops(specs[name], dict(zip(t["head"], r)), codes):
                    out.append(f"no answer in the evidence: {s}: table {name} holds a guarded code")
    return out


def eligible(result: Pool, drawn: list[str]) -> list[str]:
    """Each patient meets the cohort's requirements at the prediction time, such as an admission that is still open."""
    pair = result.pair
    reqs = _event_requirements(pair.cohort, pair.config.definitions)
    return [f"eligible at the prediction time: {s} misses a requirement of the cohort" for s in drawn
            if not all(meets(q, result.patients[s].ctx, pair.config.definitions) for q in reqs)]


def _is_event_rule(rule) -> bool:
    """An outcome read inside the anchor's visit: its positives must still be ahead of the prediction time."""
    return rule.exists is not None and rule.same_visit


def events_ahead(result: Pool, drawn: list[str]) -> list[str]:
    out = []
    for t in result.pair.template.targets:
        rule = result.pair.rule(t.label)
        if not _is_event_rule(rule):
            continue
        for s in drawn:
            p = result.patients[s]
            if p.answers[t.name] != 1 or p.ctx.anchor is None:
                continue
            times = [when(e["time"]) for e in window(p.ctx, rule, rule.exists) or ()]
            if not times or min(x for x in times if x is not None) <= p.ctx.anchor:
                out.append(f"events still ahead: {t.name}: positive {s} has its event at or before the prediction time")
    return out


def _short(values: list, metric: str) -> dict | None:
    counts: dict[str, int] = {}
    for v in values:
        if v is not None:
            counts[str(v)] = counts.get(str(v), 0) + 1
    if metric == "mae":
        return None if len(counts) >= 2 else {"reason": "fewer than 2 distinct values", "counts": counts}
    if len(counts) >= 2 and min(counts.values()) >= MIN_PER_CLASS:
        return None
    return {"reason": f"fewer than {MIN_PER_CLASS} in a class", "counts": dict(sorted(counts.items()))}


def enough_patients(result: Pool, drawn: list[str]) -> tuple[list[str], dict]:
    """Refuses a target the draw balances on; any other short target is marked and left out of scoring (Bosong, 2026-11-09)."""
    problems, marks = [], {}
    drawn_on = set(result.pair.cohort.select.by)
    for t in result.pair.template.targets:
        short = _short([result.patients[s].answers[t.name] for s in drawn], t.metric)
        if short is None:
            continue
        if t.name in drawn_on:
            problems.append(f"enough patients: target {t.name}: {short['reason']}")
        else:
            marks[t.name] = short
    return problems, marks


def answers_vary(stats: dict) -> list[str]:
    """A target with one answer across the pool refuses the whole task (R-121)."""
    return [f"answers that vary: target {t} has one answer across the pool" for t, s in stats.items() if len(s["counts"]) <= 1]
