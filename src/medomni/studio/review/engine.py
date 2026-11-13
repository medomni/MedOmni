"""The audit engine: items, DUA masking, severity and aggregation.

An item is one observation: (check, auditor, instance, outcome, detail). A check's outcome, per auditor: fail if any
item fails; else unassessed when it has no assessed evidence; else warn if any warns; else pass (Failure > Unassessed >
Warning > Pass). A cell's outcome follows the same order over its checks. Item pass rate = pass / (pass + warn + fail).

DUA: records carry counts, digests, file names and masked instance ids only. Atom names become `<template>#<sha8>`,
known subject ids `<sid>`; record-style ids are masked by pattern.

Severity: an item fails only if it harms the benchmark's main claim (the answer is reachable in the evidence, an
encoder has seen the evaluation data, a target does not mean what it says). Every other strict failure is shown as a
warning with its reason; the records keep the strict outcome. A check's strict failure is kept by check id
(`MAIN_CLAIM`), as v0.2 kept specific instances.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .matrix import FAIL, NONE, PASS, WARN

_RANK = {FAIL: 0, NONE: 1, WARN: 2, PASS: 3}
# A human sign-off is not the LLM's to give
NOT_FOR = {("T-CLIN.4", "L"), ("R-CLIN.4", "L")}
MAIN_CLAIM = {"T-ISOL.1": "the answer is reachable in the evidence",
              "T-ISOL.2": "the answer is reachable in the evidence",
              "T-ISOL.3": "the answer is reachable by the agent",
              "P-ISOL.3": "an encoder has seen the evaluation data",
              "T-CLIN.3": "the target does not mean what it says"}
DEMOTE = {
    "D-COMP": "a missing record, not an error in the data the models see",
    "D-CONF": "a declaration/supply mismatch the build converts; scores unaffected",
    "D-ISOL": "provenance/DUA housekeeping; no target information reaches the models",
    "F-COMP": "an incomplete contract record; scores unaffected",
    "F-CONF": "a reader limitation that affects encoder availability, not score validity",
    "F-ISOL": "reader metadata/tolerance issue; no target or gold information exposed",
    "F-CLIN": "degrades encoder input quality; does not make scores misstate model ability",
    "P-COMP": "missing encoder evidence/records; the encoders are optional tools",
    "P-CONF": "encoder acceptance/quality gap; the encoders are optional tools",
    "P-ISOL": "isolation hardening gap; no path to gold or evaluation data",
    "P-CLIN": "encoder output quality; an optional tool the agent must weigh itself",
    "T-COMP": "a missing record; the task artifacts that are scored are complete",
    "T-CONF": "provenance/record agreement; the scored task content is unaffected",
    "T-ISOL": "isolated or low-information case; does not reveal the answer",
    "T-CLIN": "the affected target is unscorable and drops out of the reported scores",
    "R-COMP": "a record-keeping gap; outcomes stay explicit",
    "R-CONF": "a model outcome the harness records explicitly",
    "R-ISOL": "no cross-trial or gold access",
    "R-CLIN": "model behaviour the benchmark exists to measure, not a benchmark defect",
}


@dataclass(frozen=True)
class Item:
    check: str  # e.g. "T-ISOL.1"
    auditor: str  # M | L | H
    instance: str  # masked id
    outcome: str
    detail: str = ""
    source: str = ""  # the check function, gate or review file that produced it

    @property
    def cell(self) -> str:
        return self.check.split(".")[0]


def sha8(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:8]


class Masker:
    """Every string that reaches a record goes through here. Subject ids shorter than 4 characters are not masked by
    substring (too many false hits); atom names holding them are still masked whole."""

    def __init__(self):
        self.atoms: dict[str, str] = {}
        self.sids: set[str] = set()
        self._re = None

    def register(self, atom: str, sid: str) -> None:
        self.atoms[atom] = f"{atom.split('__')[0]}#{sha8(atom)}"
        if len(sid) >= 4:
            self.sids.add(sid)
        self._re = None

    def mask(self, s: str) -> str:
        if not s:
            return s
        for a, m in self.atoms.items():
            s = s.replace(a, m)
        if self.sids:
            if self._re is None:
                alt = "|".join(sorted((re.escape(x) for x in self.sids), key=len, reverse=True))
                self._re = re.compile(rf"(?<![A-Za-z0-9])(?:{alt})(?![A-Za-z0-9])")
            s = self._re.sub("<sid>", s)
        s = re.sub(r"(?<![A-Za-z0-9])[pP]?\d{6,}_\d+", "<rec>", s)  # a waveform record's <rec>_<seg>
        return re.sub(r"(?<![A-Za-z0-9])[pP]?\d{8}(?=[_./]|\.(?:hea|dat|json|csv|edf|h5))", "<id>", s)


class Sink:
    """Collects one audit's items; `add` masks the instance and detail on the way in."""

    def __init__(self, masker: Masker):
        self.items: list[Item] = []
        self.m = masker

    def add(self, check, auditor, instance, outcome, detail="", source="") -> None:
        if outcome not in (PASS, WARN, FAIL, NONE):
            raise ValueError(outcome)
        self.items.append(Item(check, auditor, self.m.mask(str(instance)), outcome, self.m.mask(str(detail))[:400], source))


def tally(items: list[Item]) -> dict:
    c: dict = defaultdict(int)
    for i in items:
        c[i.outcome] += 1
    assessed = c[PASS] + c[WARN] + c[FAIL]
    return {"pass": c[PASS], "warn": c[WARN], "fail": c[FAIL], "unassessed": c[NONE], "assessed": assessed,
            "rate": (c[PASS] / assessed) if assessed else None}


def check_outcome(items: list[Item]) -> str:
    outs = {i.outcome for i in items}
    if FAIL in outs:
        return FAIL
    if not outs & {PASS, WARN}:
        return NONE
    return WARN if WARN in outs else PASS


def apply_severity(items: list[Item]) -> list[Item]:
    out = []
    for it in items:
        if it.outcome == FAIL and it.check in MAIN_CLAIM:
            it = Item(it.check, it.auditor, it.instance, FAIL, f"[harms main claim: {MAIN_CLAIM[it.check]}] {it.detail}"[:400], it.source)
        elif it.outcome == FAIL:
            it = Item(it.check, it.auditor, it.instance, WARN,
                      f"[strict fail, demoted: {DEMOTE.get(it.cell, 'does not harm the main claim')}] {it.detail}"[:400], it.source)
        out.append(it)
    return out


def aggregate(cells: dict, items: list[Item]) -> dict:
    """{cell: {auditor: {outcome, tally, coverage, checks: {check: {outcome, tally}}}}} for every (cell, auditor) the
    matrix assigns. An item for a check or auditor the matrix does not assign is an error."""
    by: dict = defaultdict(list)
    for it in items:
        c = cells.get(it.cell)
        if c is None or it.check not in c["checks"]:
            raise ValueError(f"item for unknown check {it.check}")
        if it.auditor not in c["auditors"]:
            raise ValueError(f"{it.check}: auditor {it.auditor} is not assigned ({c['auditors']})")
        by[(it.check, it.auditor)].append(it)
    out = {}
    for cid, c in cells.items():
        out[cid] = {}
        for a in c["auditors"]:
            checks = {}
            for k in c["checks"]:
                if (k, a) in NOT_FOR:
                    continue
                its = by.get((k, a), [])
                checks[k] = {"outcome": check_outcome(its), "tally": tally(its)}
            its = [i for k in checks for i in by.get((k, a), [])]
            outs = [v["outcome"] for v in checks.values()]
            outcome = FAIL if FAIL in outs else NONE if NONE in outs else WARN if WARN in outs else PASS
            out[cid][a] = {"outcome": outcome, "tally": tally(its), "checks": checks,
                           "coverage": (sum(1 for v in checks.values() if v["outcome"] != NONE), len(checks))}
    return out


def to_jsonl(items: list[Item]) -> str:
    return "".join(json.dumps(asdict(i)) + "\n" for i in items)


def read_jsonl(path: Path) -> list[Item]:
    if not path.exists():
        return []
    return [Item(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
