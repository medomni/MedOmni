"""MedOmni's v1 builder (R-142): one pipeline per `<template>@<cohort>`: select -> gold -> content -> render -> check.

The selection and answers are made once per pair however many arms a set lists; arms differ only in rendering (R-107).
Build stops, naming the step and the target or patient, when a correctness check fails, and writes no task that fails.
Its input format (dataset packages, templates, cohorts, labels, evidence) is its own; its output is Core's built-task
contract (`medomni.core.tasks`), checked with Core's checks over built output as well as its own refusals.
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from medomni import __version__
from medomni.core import hashing, plugins, workspace
from medomni.core.builders import TaskBuilder, arm_build
from medomni.core.cache import Cache
from medomni.core.loading import build as load_dataset
from medomni.core.tasks import checks as built_checks
from medomni.core.tasks import layout

from . import checks, content, evidence, render
from .pool import BuildError, Pool, draw, event_subjects, file_checker, load_pair, pool, read_events, source_ids

__all__ = ["BUILDER", "BuildError", "MedOmniV1", "build", "run_checks"]

BUILDER, VERSION = "medomni-v1", "1"


class _Arm:
    """An arm as this builder renders it: its build side (`medomni.arm_builds`), then its run side (`medomni.arms`)."""

    def __init__(self, run, build):
        self.run, self.build = run, build

    def __getattr__(self, key):
        return getattr(self.build, key) if hasattr(self.build, key) else getattr(self.run, key)


def _arm(name: str) -> _Arm:
    pieces = plugins.resolve(plugins.ARMS).pieces
    if name not in pieces:
        raise BuildError(f"unknown arm '{name}' (registered: {', '.join(sorted(pieces))})")
    side = arm_build(BUILDER, name)
    if side is None:
        raise BuildError(f"{BUILDER} has no build side for arm '{name}' (register {BUILDER}:{name} in medomni.arm_builds)")
    return _Arm(pieces[name].load(), side)


def _tree(ws) -> Path:
    return layout.tree(ws)


def _atom_dir(tree: Path, arm, variant, name: str) -> Path:
    return layout.atom_dir(tree, arm.name, variant, name)


def _dataset_events(pair, ws, cache) -> tuple[Path, Path]:
    raw = workspace.dataset_path(ws, pair.dataset)
    entry, _ = load_dataset(pair.package, raw, cache)
    return raw, entry.path / "events.parquet"


def _tables_for(pairs: list, raw: Path, subjects: set[str]) -> dict:
    specs = content.table_specs(pairs[0])
    wanted = [t for t in pairs[0].evidence.tables if t in specs]
    return evidence.read_tables(specs, wanted, raw, subjects)


def config_hashes(pair, arms: list) -> dict[str, str]:
    from medomni import __version__ as release

    out = {}
    for arm in arms:
        for variant in arm.variants(pair):
            files = {**pair.config_files(), **arm.definition(pair, variant), "builder": f"{BUILDER}/{VERSION}".encode()}
            key = f"{arm.name}/{variant}" if variant else arm.name
            out[key] = hashing.config_hash(files, dataset_release=pair.config.description.version, medomni_release=release)
    return out


def build(pair_ids: list[str], arm_names: list[str], ws=None, source_with=None, draw_with=None, reproduction=False,
          stream=None) -> list[Path]:
    """Build each pair under each arm. Returns the content folders.

    `source_with` and `draw_with` replace the source population and the draw, and `reproduction` skips the pool-wide
    conversion and keeps v0.2's uncut numerics files: the reproduction test only (R-118)."""
    stream = stream or sys.stdout
    ws = ws or workspace.load()
    cache = Cache(Path(ws.cache))
    tree = _tree(ws)
    arms = [_arm(a) for a in arm_names]
    pairs = [load_pair(p) for p in pair_ids]
    by_dataset = defaultdict(list)
    for p in pairs:
        by_dataset[p.dataset].append(p)
    done = []
    for dataset, group in by_dataset.items():
        raw, events_path = _dataset_events(group[0], ws, cache)
        everyone = event_subjects(events_path)
        sources = {p.id: (source_with(p) if source_with else source_ids(p, everyone)) for p in group}
        events = read_events(events_path, set().union(*sources.values()))
        results, drawn = {}, {}
        for p in group:
            r = pool(p, events, sources[p.id])
            check = None if reproduction or draw_with else file_checker(p, raw, cache)
            if check is None and not reproduction:
                r.counts["file check"] = len(r.patients)
            drawn[p.id], results[p.id] = (draw_with(r) if draw_with else draw(r, check)), r
            print(f"{p.id}: pool {len(r.patients)}, drawn {len(drawn[p.id])}", file=stream)
        tables = _tables_for(group, raw, set().union(*drawn.values()))
        for p in group:
            done.append(_finish(results[p.id], drawn[p.id], raw, tables, tree, arms, cache, stream, reproduction))
    return done


def _finish(result: Pool, drawn: list[str], raw: Path, tables, tree: Path, arms: list, cache, stream, reproduction=False) -> Path:
    pair = result.pair
    recs = content.records(result, drawn, raw, tables)
    stats = content.pool_stats(result)
    short_problems, marks = checks.enough_patients(result, drawn)
    specs = content.table_specs(pair)
    problems = (checks.leak(pair, recs, specs) + checks.eligible(result, drawn) + checks.events_ahead(result, drawn)
                + short_problems + checks.answers_vary(stats))
    if problems:
        raise BuildError(f"{pair.id}: " + "; ".join(problems[:5]) + (f"; and {len(problems) - 5} more" if len(problems) > 5 else ""))
    folder = content.write(result, drawn, recs, tree / "_content")
    meta = json.loads((folder / "content.json").read_text(encoding="utf-8"))
    for t in meta["targets"]:
        if t["name"] in marks:
            t["too_few"] = marks[t["name"]]
    (folder / "content.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    hook, params = content.views(pair)
    repo = pair.package.parent.parent.parent
    for arm in arms:
        for variant in arm.variants(pair):
            for s in drawn:
                name = content.atom_name(pair, s)
                d = _atom_dir(tree, arm, variant, name)
                rec = arm.mask(recs[s], variant, pair) if variant else recs[s]
                inv = render.atom(pair, arm, variant, rec, d, raw, cache, hook, params, repo, crop=not reproduction)
                bad = arm.check(pair, variant, inv, s) + built_checks.atom_checks(d)
                if bad:
                    shutil.rmtree(d, ignore_errors=True)
                    raise BuildError(f"{pair.id}: " + "; ".join(bad[:5]))
    (folder / "manifest.json").write_text(json.dumps({"pair": pair.id, "config_hash": config_hashes(pair, arms),
                                                     "builder": f"{BUILDER}/{VERSION}", "counts": result.counts,
                                                     "release": __version__}, indent=1) + "\n", encoding="utf-8")
    print(f"{pair.id}: built {len(drawn)} atoms under {', '.join(a.name for a in arms)}", file=stream)
    return folder


def run_checks(pair_id: str, ws=None, arm_names=None) -> list[str]:
    """`studio task check <pair>`: this builder's refusals on what it wrote, then Core's checks over built output."""
    ws = ws or workspace.load()
    pair, tree, cache = load_pair(pair_id), _tree(ws), Cache(Path(ws.cache))
    folder = layout.content_dir(tree, pair_id)
    if not (folder / "content.json").is_file():
        return [f"{pair_id}: nothing built yet; run `medomni studio task build {pair_id}`"]
    meta = json.loads((folder / "content.json").read_text(encoding="utf-8"))
    drawn = [a["subject"] for a in meta["atoms"]]
    _, events_path = _dataset_events(pair, ws, cache)
    result = pool(pair, read_events(events_path, set(drawn)), set(drawn))
    recs = {a["subject"]: json.loads((folder / a["atom"] / "record.json").read_text(encoding="utf-8")) for a in meta["atoms"]}
    out = (checks.leak(pair, recs, content.table_specs(pair)) + checks.eligible(result, drawn)
           + checks.events_ahead(result, drawn) + checks.enough_patients(result, drawn)[0] + checks.answers_vary(meta["pool_stats"]))
    return out + built_checks.task_checks(tree, pair_id, arm_names or _built_arms(tree, meta))


def _built_arms(tree: Path, meta: dict) -> list[str]:
    """The arms a task was built under, from its manifest's config hashes."""
    keys = layout.read_json(tree, meta["pair"], "manifest.json")["config_hash"]
    return sorted({k.split("/", 1)[0] for k in keys})


class MedOmniV1(TaskBuilder):
    """MedOmni's v1 builder, registered in `medomni.builders` (R-142)."""

    name, version = BUILDER, VERSION

    def config_files(self, task: str, arm: str, variant: str | None) -> dict[str, Path | bytes]:
        pair, a = load_pair(task), _arm(arm)
        return {**pair.config_files(), **a.definition(pair, variant), "builder": f"{BUILDER}/{VERSION}".encode()}

    def build(self, tasks: list[str], arms: list[str], workspace_=None) -> list[Path]:
        return build(tasks, arms, ws=workspace_)


builder = MedOmniV1()
