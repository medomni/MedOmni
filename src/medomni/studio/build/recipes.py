"""Recipes across files (part 6): checks a contract model can't make alone, because they span files.

Each file's own fields are checked by its contract (`Cohort`, `LabelLibrary`, `EvidenceRules`). Here:

- a cohort's `has_label` and `draw.by` name targets of its template; each target's label (`<dataset>:<label>`)
  names its own dataset and a label in that dataset's `labels.yaml`;
- a `definition` requirement names a definition in `dataset.yaml`; a `files` requirement names known families;
- every code a cohort, label or guard names, as a code or a pattern, matches a code in `codes.csv` or a shared code;
- evidence rules name tables `dataset.yaml` reads.

Running a recipe is Build's job (Bench, Stage 3).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from medomni.core.loading import SHARED

_META = re.compile(r"[\\^$.|?*+()\[\]{}]")


def _known(pattern: str, codes: set[str]) -> bool:
    try:
        rx = re.compile(pattern)
    except re.error:
        return False
    if any(rx.search(c) for c in codes):
        return True
    literal = _META.split(pattern.lstrip("^"), 1)[0]  # the fixed start of the pattern
    return bool(SHARED.match(literal) or SHARED.match(literal + "X"))


def _codes(where: str, pats, codes, out):
    if codes is None:
        return
    for p in pats:
        if not _known(p, codes):
            out.append(f"{where}: code {p!r} matches nothing in codes.csv and no shared code")


def check_labels(labels, codes: set[str] | None) -> list[str]:
    out = []
    for name, lab in labels.root.items():
        _codes(f"label {name}", [x for x in (lab.exists, lab.none, lab.value) if x], codes, out)
        _codes(f"label {name} guard", lab.guard.codes, codes, out)
        for i, case in enumerate(lab.cases or ()):
            v = case.when.get("value") or case.when.get("exists")
            if v:
                _codes(f"label {name} case {i + 1}", [v], codes, out)
    return out


def check_cohort(name: str, cohort, *, dataset: str, targets: dict[str, str], labels, definitions: set[str] | None,
                 codes: set[str] | None, families: set[str]) -> list[str]:
    from medomni.core.contracts.recipe import Any_, Definition, Files, HasLabel, None_

    out = []
    for t, ref in targets.items():
        ds, _, label = ref.partition(":")
        if ds != dataset:
            out.append(f"{name}: target {t} names a label of {ds}, not of {dataset}")
        elif label not in labels.root:
            out.append(f"{name}: target {t} names label {label!r}, which {dataset}'s labels.yaml lacks")
    for b in cohort.draw.by:
        if b not in targets:
            out.append(f"{name}: draw.by names {b!r}, which is not a target of the template")
    _codes(f"{name} anchor", [cohort.anchor.event], codes, out)
    for i, q in enumerate(cohort.require, 1):
        where = f"{name} require {i}"
        if isinstance(q, HasLabel) and q.has_label not in targets:
            out.append(f"{where}: has_label names {q.has_label!r}, which is not a target of the template")
        elif isinstance(q, Definition) and definitions is not None and q.definition not in definitions:
            out.append(f"{where}: definition {q.definition!r} is not in dataset.yaml's definitions")
        elif isinstance(q, Files):
            out += [f"{where}: unknown family {f!r}" for f in q.files if f not in families]
        elif isinstance(q, (Any_, None_)):
            _codes(where, q.any if isinstance(q, Any_) else q.none, codes, out)
    return out


def check_evidence(evidence, tables: set[str] | None) -> list[str]:
    if tables is None:
        return []
    return [f"evidence: table {t!r} is not a table dataset.yaml reads" for t in evidence.tables if t not in tables]


def check_package(package: str | Path) -> list[str]:
    """Every cross-file check for one dataset package: its labels, evidence, and each template's cohorts."""
    from medomni.core import families as registry
    from medomni.core.contracts import (Cohort, DatasetConfig, EvidenceRules, LabelLibrary, TaskTemplate, load)
    from medomni.core.loading.options import options

    package = Path(package)
    config = load(package / "dataset.yaml", DatasetConfig)
    with open(package / "codes.csv", newline="", encoding="utf-8") as f:
        codes = {r["code"] for r in csv.DictReader(f)}
    tables = {n for r in config.read if r.reader == "csv" for n in options(r).tables}
    labels = load(package / "labels.yaml", LabelLibrary)
    out = check_labels(labels, codes)
    if (package / "evidence.yaml").is_file():
        out += check_evidence(load(package / "evidence.yaml", EvidenceRules), tables)
    fams = set(registry.load_registry())
    for tdir in sorted((package / "tasks").glob("*/")):
        tpl = load(tdir / "template.yaml", TaskTemplate)
        targets = {t.name: t.label for t in tpl.targets}
        for cp in sorted((tdir / "cohorts").glob("*.yaml")):
            if cp.name.endswith(".tests.yaml"):
                continue
            out += check_cohort(f"{tpl.template_id}@{cp.stem}", load(cp, Cohort), dataset=package.name,
                                targets=targets, labels=labels, definitions=set(config.definitions), codes=codes,
                                families=fams)
    return out
