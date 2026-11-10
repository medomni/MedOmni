"""What several tools read: built tasks, the results file, a run's folder, tables as text."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .tools import ToolError


def tree(ws) -> Path:
    return Path(ws.tasks) / "atomtasks"


def pairs_of(target: str) -> list[str]:
    """The pairs a command names: one `<template>@<cohort>`, or a set `<benchmark>/<set>`."""
    if "@" in target:
        return [target]
    from medomni.studio.build import BuildError
    from medomni.studio.build.sets import load_set

    try:
        task_set, _ = load_set(target)
    except BuildError as e:
        raise ToolError(str(e)) from None
    return [e.task for e in task_set.tasks]


def built_pairs(ws) -> list[str]:
    """Every pair with built content in the workspace."""
    return sorted(p.name for p in (tree(ws) / "_content").glob("*") if (p / "content.json").is_file())


def content(ws, pair: str) -> dict | None:
    p = tree(ws) / "_content" / pair / "content.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def manifest(ws, pair: str) -> dict | None:
    p = tree(ws) / "_content" / pair / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def load_pair(pair: str):
    from medomni.studio.build import BuildError
    from medomni.studio.build.pool import load_pair as bench_load

    try:
        return bench_load(pair)
    except (BuildError, FileNotFoundError) as e:
        raise ToolError(str(e)) from None


def arms(pair) -> list[tuple[object, str | None]]:
    """(arm, variant) for every arm registered in `medomni.arms` that the v1 builder builds, and each of its variants."""
    from medomni.core import plugins
    from medomni.studio.build import BuildError, _arm

    out = []
    for name in sorted(plugins.resolve(plugins.ARMS).pieces):
        try:
            arm = _arm(name)
        except BuildError:  # an arm this builder has no build side for
            continue
        for variant in arm.variants(pair) if _has_variants(arm, pair) else (None,):
            out.append((arm, variant))
    return out


def _has_variants(arm, pair) -> bool:
    try:
        arm.variants(pair)
    except FileNotFoundError:  # the ladder arm's file: not every template has one
        return False
    return True


def atom_dir(root: Path, arm_name: str, variant, atom: str) -> Path:
    return root / arm_name / variant / atom if variant else root / arm_name / atom


def built_atoms(ws, pair_id: str, meta: dict | None = None) -> list[tuple[str, str | None, str, Path]]:
    """(arm, variant, atom name, folder) of every atom rendered for a pair."""
    meta = meta or content(ws, pair_id)
    if meta is None:
        return []
    pair, root, out = load_pair(pair_id), tree(ws), []
    for arm, variant in arms(pair):
        for a in meta["atoms"]:
            d = atom_dir(root, arm.name, variant, a["atom"])
            if d.is_dir():
                out.append((arm.name, variant, a["atom"], d))
    return out


def results(ws) -> tuple[list, list]:
    """(run records, score records) of the workspace's results file, the latest line of each (R-77, append-only).
    Records with the same id overwrite earlier ones, as `medomni bench score` appends new rows beside old ones."""
    from medomni.core.contracts import ContractError, ResultRecord, RunRecord
    from pydantic import TypeAdapter

    path = Path(ws.results)
    if not path.is_file():
        return [], []
    adapter = TypeAdapter(ResultRecord)
    latest: dict = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = adapter.validate_json(line)
        except ValueError as e:
            raise ContractError(f"{path}:{n}", [("", str(e))]) from None
        key = (rec.run_id, None) if isinstance(rec, RunRecord) else (rec.run_id, rec.target)
        latest[(rec.kind, *key)] = rec
    runs = [r for r in latest.values() if r.kind == "run"]
    scores = [r for r in latest.values() if r.kind == "score"]
    return runs, scores


def run_dir(ws, run: str) -> Path:
    d = Path(ws.runs) / run
    if not d.is_dir():
        raise ToolError(f"no run '{run}' under {ws.runs}")
    return d


def table(head: list[str], rows: list[list]) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
                     + ["| " + " | ".join("—" if c is None else str(c) for c in r) + " |" for r in rows])


def group(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[key(r)].append(r)
    return out


ENCODERS = "perception/encoders"


def encoders_root() -> Path:
    from medomni.core import plugins

    repo = plugins.find_repo()
    if repo is None:
        raise ToolError("no MedOmni repository found; encoder folders are read from a clone")
    return repo / ENCODERS


def encoder_dirs() -> list[Path]:
    root = encoders_root()
    return sorted(d for f in root.iterdir() if f.is_dir() for d in f.iterdir() if d.is_dir() and (d / "card.yaml").is_file())


def encoder_id(edir: Path) -> str:
    return f"{edir.parent.name}__{edir.name}"


def encoder_dir(eid: str) -> Path:
    family, _, name = eid.partition("__")
    d = encoders_root() / family / name
    if not name or not (d / "card.yaml").is_file():
        raise ToolError(f"no such encoder: {eid} (write <family>__<encoder>)")
    return d
