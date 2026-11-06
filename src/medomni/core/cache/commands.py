"""`medomni cache build|status|verify|gc`."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import TMP, Cache, current_steps, in_use, size, verify



def _cache() -> Cache:
    from medomni.core import workspace

    return Cache(Path(workspace.load().cache))


def _mib(n: int) -> str:
    return f"{n / (1 << 20):.1f} MiB"


def cmd_build(a) -> int:
    from medomni.core import loading, workspace

    cfg = workspace.load()
    package = loading.find_package(a.dataset)
    raw = workspace.dataset_path(cfg, package.name)
    entry, created = loading.build(package, raw, Cache(Path(cfg.cache)))
    state = "built" if created else "already in the cache"
    print(f"{entry.name}: {state}; {entry.meta.rows.get('events', 0)} events, content hash {entry.meta.content_hash}")
    return 0


def cmd_status(a) -> int:
    cache, steps = _cache(), current_steps()
    rows: dict[tuple[str, str], list] = {}
    tmp = 0
    for d in cache.folders():
        if TMP in d.name:
            tmp += 1
            continue
        e = cache.read(d)
        r = rows.setdefault((e.meta.dataset, e.meta.step), [0, 0, 0])
        r[0] += 1
        r[1] += size(d)
        r[2] += in_use(e, steps)
    print(f"cache: {cache.root}")
    if not rows and not tmp:
        print("no entries")
        return 0
    print(f"  {'dataset':<16} {'step':<24} {'entries':>7} {'size':>12} {'in use':>7}")
    for (dataset, step), (n, b, used) in sorted(rows.items()):
        print(f"  {dataset:<16} {step:<24} {n:>7} {_mib(b):>12} {used:>7}")
    if tmp:
        print(f"  {tmp} unfinished {TMP} folder(s); `medomni cache gc` removes them")
    return 0


def _published(name: str) -> tuple[str, list]:
    from medomni.core.contracts import TaskSet, load

    p = Path(name)
    if not p.suffix:
        from medomni.core import plugins

        repo = plugins.find_repo()
        if repo is None:
            raise FileNotFoundError(f"task set '{name}': give a path, or run inside the repository")
        p = repo / "bench/sets" / f"{name}.yaml"
    s = load(p, TaskSet)
    return s.name, [(e.task, u) for e in s.tasks for u in e.cache]


def cmd_verify(a) -> int:
    cache = _cache()
    bad = n = 0
    for e in cache.entries():
        n += 1
        for problem in verify(e):
            bad += 1
            print(f"FAIL  {e.name}: {problem}")
    print(f"{n} entries checked, {bad} problem(s)")
    if a.set:
        set_name, uses = _published(a.set)
        differ = 0
        for task, use in uses:
            e = cache.find(use.key)
            if e is None:
                differ += 1
                print(f"MISSING  {task}: entry {use.key} is not in your cache")
            elif e.meta.content_hash != use.content_hash:
                differ += 1
                print(f"DIFFERS  {task}: {e.name} has content hash {e.meta.content_hash}, "
                      f"published {use.content_hash}")
        print(f"task set {set_name}: {len(uses) - differ}/{len(uses)} published entries match")
        bad += differ
    return 1 if bad else 0


def cmd_gc(a) -> int:
    cache, steps = _cache(), current_steps()
    doomed = []
    for d in cache.folders():
        if TMP in d.name:
            doomed.append((d, "unfinished"))
        elif not in_use(cache.read(d), steps):
            doomed.append((d, "no current step uses it"))
    for d, why in doomed:
        print(f"{'would remove' if a.dry_run else 'removed'}  {d.relative_to(cache.root)}  ({why})")
        if not a.dry_run:
            shutil.rmtree(d)
    print(f"{len(doomed)} folder(s) {'to remove' if a.dry_run else 'removed'}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="medomni cache", description="Build, list, verify and clean the cache.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="load a dataset into the cache (file conversions come with Bench's Build, Stage 3)")
    b.add_argument("dataset")
    sub.add_parser("status", help="entries per dataset and step, with size and whether a current step uses them")
    v = sub.add_parser("verify", help="recompute every content hash")
    v.add_argument("--set", help="also compare with a task set's published hashes (a name or a path)")
    g = sub.add_parser("gc", help="remove entries no current step uses, and unfinished folders")
    g.add_argument("--dry-run", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    from medomni.core.contracts import ContractError
    from medomni.core.loading import LoadError
    from medomni.core.workspace import WorkspaceError

    except_types = (WorkspaceError, ContractError, FileNotFoundError, LoadError)
    try:
        return {"build": cmd_build, "status": cmd_status, "verify": cmd_verify, "gc": cmd_gc}[a.cmd](a)
    except except_types as e:
        print(f"medomni cache {a.cmd}: {e}", file=sys.stderr)
        return 2
