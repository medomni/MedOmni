"""From the event table to the drawn patients: source population, prediction time, requirements, labels, file check, draw.

Each stage leaves a count behind (the step counts in the build manifest). Nothing here reads a raw file except the file
check, which goes through Core's cached conversions.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from medomni.core.contracts import Cohort, DatasetConfig, EvidenceRules, LabelLibrary, TaskTemplate
from medomni.core.contracts import load as load_contract
from medomni.core.contracts.recipe import Any_, Converts, Definition, Files, HasLabel, None_

from .labels import Context, anchor, label, window

MIN_PER_CLASS = 5  # used by the feasibility check


class BuildError(RuntimeError):
    """Build refuses: the message names the step and the target or patient."""


@dataclass(frozen=True)
class Pair:
    """One `<template>@<cohort>` and everything its package says about it."""

    id: str
    package: Path
    template: TaskTemplate
    cohort: Cohort
    cohort_name: str
    labels: LabelLibrary
    config: DatasetConfig
    evidence: EvidenceRules

    @property
    def dataset(self) -> str:
        return self.template.dataset

    @property
    def folder(self) -> Path:
        return self.package / "tasks" / self.template.template_id

    def rule(self, label_ref: str):
        return self.labels.root[label_ref.split(":", 1)[1]]

    def config_files(self) -> dict[str, Path]:
        """The files a pair's config hash covers before the arm's own (R-111), by repository-relative name."""
        repo = self.package.parent.parent.parent
        files = [self.folder / "template.yaml", self.folder / "cohorts" / f"{self.cohort_name}.yaml",
                 self.package / "labels.yaml", self.package / "evidence.yaml"]
        return {p.relative_to(repo).as_posix(): p for p in files}


def parse(pair: str) -> tuple[str, str, str]:
    """(template, evidence, cohort) of `<template>[:<evidence>]@<cohort>`."""
    head, _, cohort = pair.partition("@")
    template, _, evidence = head.partition(":")
    if not cohort or "_" not in template:
        raise BuildError(f"'{pair}' is not <template>@<cohort>")
    return template, evidence or "default", cohort


def load_pair(pair: str) -> Pair:
    from medomni.core.loading import find_package

    template_id, evidence, cohort = parse(pair)
    if evidence != "default":
        raise BuildError(f"{pair}: the {evidence} evidence variant is not built in v0.3.0")
    package = find_package(template_id.split("_", 1)[0])
    folder = package / "tasks" / template_id
    if not (folder / "template.yaml").is_file():
        raise BuildError(f"{pair}: no template at {folder}")
    if not (folder / "cohorts" / f"{cohort}.yaml").is_file():
        raise BuildError(f"{pair}: no cohort {cohort}")
    return Pair(pair, package, load_contract(folder / "template.yaml", TaskTemplate),
                load_contract(folder / "cohorts" / f"{cohort}.yaml", Cohort), cohort,
                load_contract(package / "labels.yaml", LabelLibrary), load_contract(package / "dataset.yaml", DatasetConfig),
                load_contract(package / "evidence.yaml", EvidenceRules))


def in_fraction(salt: str, subject: str, f: float) -> bool:
    return int(hashlib.sha256(f"{salt}|{subject}".encode()).hexdigest(), 16) / 2 ** 256 < f


def source_ids(pair: Pair, subjects) -> set[str]:
    """The cohort's source population (Recipes page): the dataset's hash rule, or a smaller fraction the cohort sets."""
    src, rule = pair.cohort.source, pair.config.source
    if src == "all" or rule == "all":
        return set(subjects)
    f = src.fraction if src.fraction is not None else rule.fraction
    return {s for s in subjects if in_fraction(rule.salt, s, f)}


def read_events(path: Path, subjects: set[str] | None = None) -> dict[str, list[dict]]:
    """One list of event rows per subject, in event-table order."""
    import pyarrow.parquet as pq

    filters = [("subject_id", "in", sorted(subjects))] if subjects is not None else None
    out = defaultdict(list)
    for row in pq.read_table(path, filters=filters).to_pylist():
        out[row["subject_id"]].append(row)
    return dict(out)


def event_subjects(path: Path) -> list[str]:
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    return pc.unique(pq.read_table(path, columns=["subject_id"]).column("subject_id")).to_pylist()


@dataclass
class Patient:
    id: str
    ctx: Context
    answers: dict[str, object]  # target -> value
    balance: dict[str, object]  # balance label -> value

    @property
    def time(self) -> str:
        return "" if self.ctx.anchor is None else str(self.ctx.anchor)


@dataclass
class Pool:
    pair: Pair
    patients: dict[str, Patient]
    counts: dict[str, int] = field(default_factory=dict)


def meets(q, ctx: Context, definitions: dict) -> bool:
    """One requirement that needs only the events."""
    if isinstance(q, Definition):
        return meets(definitions[q.definition], ctx, definitions)
    if isinstance(q, Any_):
        return bool(window(ctx, q, q.any))
    if isinstance(q, None_):
        hits = window(ctx, q, q.none)
        return hits is not None and not hits
    if isinstance(q, Files):
        return all(window(ctx, q, f"FILE//{f}") for f in q.files)
    raise TypeError(type(q))


def _event_requirements(cohort, definitions):
    def resolved(q):
        return definitions[q.definition] if isinstance(q, Definition) else q

    return [q for q in cohort.require if not isinstance(resolved(q), (HasLabel, Converts))]


def pool(pair: Pair, events: dict[str, list[dict]], source: set[str], hooks=None) -> Pool:
    """Prediction time, requirements and labels for every source patient."""
    defs = pair.config.definitions
    reqs = _event_requirements(pair.cohort, defs)
    must = {q.has_label for q in pair.cohort.require if isinstance(q, HasLabel)} | set(pair.cohort.draw.by)
    counts = {"source population": len(source)}
    anchored = {}
    for s in sorted(source):
        ctx = anchor(events.get(s, ()), pair.cohort.anchor)
        if ctx is not None:
            anchored[s] = ctx
    counts["prediction time"] = len(anchored)
    required = {s: c for s, c in anchored.items() if all(meets(q, c, defs) for q in reqs)}
    counts["requirements"] = len(required)
    patients = {}
    for s, ctx in required.items():
        answers = {t.name: label(pair.rule(t.label), ctx, hooks) for t in pair.template.targets}
        if any(answers[m] is None for m in must):
            continue
        balance = {b: label(pair.labels.root[b], ctx, hooks) for b in pair.cohort.draw.balance}
        if any(v is None for v in balance.values()):
            continue
        patients[s] = Patient(s, ctx, answers, balance)
    counts["labels"] = len(patients)
    return Pool(pair, patients, counts)


def _convert_one(args):
    cache_root, converter_name, dataset, raw_root, rel, family, raw_hash = args
    from medomni.core.cache import Cache
    from medomni.core.families import converters

    try:
        converters.cached(Cache(Path(cache_root)), converters.load().found[converter_name], dataset, Path(raw_root), rel,
                          family, raw_hash)
        return True
    except Exception:  # a night this family can't be made from
        return False


def needs_converting(path: str) -> bool:
    """A file whose format a converter reads, rather than one a family accepts as it is."""
    from medomni.core.families import converters

    return Path(path).suffix[1:] in {c.source_format for c in converters.load().found.values()}


def converted_files(p: Patient) -> list[tuple[str, str]]:
    """(family, raw path) of each file this patient's atom needs converted (Families page)."""
    return [(e["code"][6:], e["path"]) for e in p.ctx.events if e["code"].startswith("FILE//") and needs_converting(e["path"] or "")]


def file_check(result: Pool, raw_root: Path, cache, workers: int = 6) -> Pool:
    """The `converts` requirement: run before the draw, so the pool does not depend on the seed."""
    from multiprocessing import get_context

    from medomni.core import hashing
    from medomni.core.families import converters

    rule = next((q.converts for q in result.pair.cohort.require if isinstance(q, Converts)), None)
    if rule is None:
        result.counts["file check"] = len(result.patients)
        return result
    jobs, hashes = [], {}
    found = converters.load()
    for p in result.patients.values():
        for family, rel in converted_files(p):
            raw_hash = hashes.setdefault(rel, hashing.quick_id(Path(raw_root) / rel))
            jobs.append((str(cache.root), converters.for_family(family, Path(rel).suffix[1:], found).name, result.pair.dataset,
                         str(raw_root), rel, family, raw_hash))
    with get_context("spawn").Pool(workers) as ex:
        done = ex.map(_convert_one, jobs, chunksize=4)
    made = defaultdict(int)
    for job, ok in zip(jobs, done):
        made[job[4]] += ok  # per night
    for p in list(result.patients.values()):
        if sum(made[rel] for rel in {r for _, r in converted_files(p)}) < rule.min_families:
            del result.patients[p.id]
    result.counts["file check"] = len(result.patients)
    return result


def _rank(seed, subject: str, time: str) -> str:
    return hashlib.sha256(f"{seed}|{subject}|{time}".encode()).hexdigest()


def _split(n: int, cells: int) -> list[int]:
    base, extra = divmod(n, cells)
    return [base + (1 if i < extra else 0) for i in range(cells)]


def cell_of(p: Patient, cohort: Cohort) -> tuple:
    return tuple(p.answers[b] for b in cohort.draw.by) + tuple(p.balance[b] for b in cohort.draw.balance)


def draw(result: Pool) -> list[str]:
    """The drawn patients (R-36): n split evenly across the cells of `by` and `balance`, ranked by hash in each."""
    cohort = result.pair.cohort
    cells = defaultdict(list)
    for p in result.patients.values():
        cells[cell_of(p, cohort)].append(p)
    if not cohort.draw.by and not cohort.draw.balance:
        cells = {(): list(result.patients.values())}
    out = []
    for key, k in zip(sorted(cells), _split(cohort.draw.n, len(cells))):
        ranked = sorted(cells[key], key=lambda p: _rank(cohort.draw.seed, p.id, p.time))
        if len(ranked) < k:
            raise BuildError(f"{result.pair.id}: draw: class {key} has {len(ranked)} patients, needs {k}")
        out += [p.id for p in ranked[:k]]
    result.counts["draw"] = len(out)
    return out
