"""`medomni cache build|status|gc`, on the workspace's cache backend."""
from __future__ import annotations

import argparse
import sys

from . import CacheError, of


def _mib(n: int) -> str:
    return f"{n / (1 << 20):.1f} MiB"


def _feature(cache, name: str):
    f = getattr(cache, name, None)
    if f is None:
        raise CacheError(f"the '{cache.name}' cache backend has no `{name}`")
    return f


def cmd_build(a) -> int:
    from medomni.core import loading, workspace

    cfg = workspace.load()
    package = loading.find_package(a.dataset)
    raw = workspace.dataset_path(cfg, package.name)
    result, created = loading.build(package, raw, of(cfg))
    state = "built" if created else "already in the cache"
    print(f"{result.name}: {state}; {result.rows.get('events', 0)} events")
    return 0


def cmd_status(a) -> int:
    from medomni.core import workspace

    cache = of(workspace.load())
    s = _feature(cache, "status")()
    print(f"cache: {cache.name} at {s['where']}")
    if not s["rows"] and not s["unfinished"]:
        print("no results")
        return 0
    print(f"  {'dataset':<16} {'step':<24} {'results':>7} {'size':>12} {'in use':>7}")
    for dataset, step, n, b, used in s["rows"]:
        print(f"  {dataset:<16} {step:<24} {n:>7} {_mib(b):>12} {used:>7}")
    if s["unfinished"]:
        print(f"  {s['unfinished']} unfinished folder(s); `medomni cache gc` removes them")
    return 0


def cmd_gc(a) -> int:
    from medomni.core import workspace

    cache = of(workspace.load())
    doomed = _feature(cache, "gc")(dry_run=a.dry_run)
    for d, why in doomed:
        print(f"{'would remove' if a.dry_run else 'removed'}  {d}  ({why})")
    print(f"{len(doomed)} folder(s) {'to remove' if a.dry_run else 'removed'}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="medomni cache", description="Build, list and clean the cache.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="load a dataset's event table into the cache")
    b.add_argument("dataset")
    sub.add_parser("status", help="results per dataset and step, with size and whether a current step uses them")
    g = sub.add_parser("gc", help="remove results no current step uses, and unfinished folders")
    g.add_argument("--dry-run", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    from medomni.core.contracts import ContractError
    from medomni.core.loading import LoadError
    from medomni.core.workspace import WorkspaceError

    except_types = (WorkspaceError, ContractError, FileNotFoundError, LoadError, CacheError)
    try:
        return {"build": cmd_build, "status": cmd_status, "gc": cmd_gc}[a.cmd](a)
    except except_types as e:
        print(f"medomni cache {a.cmd}: {e}", file=sys.stderr)
        return 2
