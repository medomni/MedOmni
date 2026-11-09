"""Build: one pipeline per `<template>@<cohort>`: draw -> gold -> content -> render -> check (Build page).

The draw and answers are made once per pair however many arms a set lists; arms differ only in rendering (R-107).
Build stops, naming the step and the target or patient, when a correctness check fails, and writes no task that fails.
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from medomni import __version__
from medomni.core import hashing, workspace
from medomni.core.cache import Cache
from medomni.core.loading import build as load_dataset

from . import checks, content, evidence, render
from .pool import BuildError, Pool, draw, event_subjects, file_check, load_pair, pool, read_events, source_ids

__all__ = ["BuildError", "build", "run_checks"]


def _arm(name: str):
    from medomni.core import plugins

    pieces = plugins.resolve(plugins.ARMS).pieces
    if name not in pieces:
        raise BuildError(f"unknown arm '{name}' (registered: {', '.join(sorted(pieces))})")
    return pieces[name].load()


def _tree(ws) -> Path:
    return Path(ws.tasks) / "atomtasks"


def _atom_dir(tree: Path, arm, variant, name: str) -> Path:
    return tree / arm.name / variant / name if variant else tree / arm.name / name


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
            files = {**pair.config_files(), **arm.definition(pair, variant)}
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
            r = r if reproduction else file_check(r, raw, cache)
            drawn[p.id], results[p.id] = (draw_with(r) if draw_with else draw(r)), r
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
                bad = arm.check(pair, variant, inv, s) + checks.atom_checks(d, rec["prediction_time"])
                if bad:
                    shutil.rmtree(d, ignore_errors=True)
                    raise BuildError(f"{pair.id}: " + "; ".join(bad[:5]))
    (folder / "manifest.json").write_text(json.dumps({"pair": pair.id, "config_hash": config_hashes(pair, arms),
                                                     "counts": result.counts, "release": __version__}, indent=1) + "\n", encoding="utf-8")
    print(f"{pair.id}: built {len(drawn)} atoms under {', '.join(a.name for a in arms)}", file=stream)
    return folder


def run_checks(pair_id: str, ws=None, arm_names=None) -> list[str]:
    """`bench task check <pair>`: the 8 checks on what Build wrote."""
    ws = ws or workspace.load()
    pair, tree, cache = load_pair(pair_id), _tree(ws), Cache(Path(ws.cache))
    folder = tree / "_content" / pair_id
    if not (folder / "content.json").is_file():
        return [f"{pair_id}: nothing built yet; run `medomni bench task build {pair_id}`"]
    meta = json.loads((folder / "content.json").read_text(encoding="utf-8"))
    drawn = [a["subject"] for a in meta["atoms"]]
    _, events_path = _dataset_events(pair, ws, cache)
    result = pool(pair, read_events(events_path, set(drawn)), set(drawn))
    recs = {a["subject"]: json.loads((folder / a["atom"] / "record.json").read_text(encoding="utf-8")) for a in meta["atoms"]}
    out = (checks.leak(pair, recs, content.table_specs(pair)) + checks.eligible(result, drawn)
           + checks.events_ahead(result, drawn) + checks.enough_patients(result, drawn)[0] + checks.answers_vary(meta["pool_stats"]))
    for arm in [_arm(a) for a in (arm_names or sorted({*(_built_arms(tree, meta))}))]:
        for variant in arm.variants(pair):
            for a in meta["atoms"]:
                d = _atom_dir(tree, arm, variant, a["atom"])
                if d.is_dir():
                    out += checks.atom_checks(d, a["prediction_time"])
    return out


def _built_arms(tree: Path, meta: dict) -> list[str]:
    from medomni.core import plugins

    names = plugins.resolve(plugins.ARMS).pieces
    return [n for n in names if (tree / n).is_dir()]
