"""`medomni bench`.

Every command the CLI page lists has a slot here. Until the Stage 3 part that builds it lands, it exits 2 and names
that part.
"""
from __future__ import annotations

import argparse
import sys

# command -> the Stage 3 part that builds it
PENDING = {
    "task new": 3, "task build": 3, "task check": 3,
    "agent new": 5, "run": 5, "score": 5,
}
CHECK_SET_PART = 4  # `task check --set` and `--release`


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="medomni bench", description="Build tasks, run agents and score them.")
    sub = ap.add_subparsers(dest="cmd", metavar="<command>")

    data = sub.add_parser("data", help="connect and check your copy of a dataset; write a new dataset package")
    dsub = data.add_subparsers(dest="sub", metavar="<data command>", required=True)
    c = dsub.add_parser("connect", help="record where your copy of a dataset is")
    c.add_argument("dataset")
    c.add_argument("--path", required=True)
    dsub.add_parser("check", help="check your copy against its dataset package").add_argument("dataset")
    dsub.add_parser("new", help="write a dataset package to fill in").add_argument("dataset")

    task = sub.add_parser("task", help="write, build and check tasks")
    tsub = task.add_subparsers(dest="sub", metavar="<task command>", required=True)
    n = tsub.add_parser("new", help="write a task template and an n20 cohort to fill in")
    n.add_argument("template")
    n.add_argument("--dataset", required=True)
    b = tsub.add_parser("build", help="build atom tasks for a set or a pair")
    b.add_argument("pair", nargs="?", help="<template>@<cohort>")
    b.add_argument("--set", help="<benchmark>/<set>")
    b.add_argument("--arm", action="append", help="an arm the set lists (default: every arm it lists)")
    k = tsub.add_parser("check", help="check a pair, every pair a set pins, or every pinned pair for a release")
    k.add_argument("pair", nargs="?", help="<template>@<cohort>")
    k.add_argument("--set", help="<benchmark>/<set>")
    k.add_argument("--release", action="store_true", help="every pinned pair in every set (MedOmni releases)")

    agent = sub.add_parser("agent", help="write an agent config")
    asub = agent.add_subparsers(dest="sub", metavar="<agent command>", required=True)
    asub.add_parser("new", help="write an agent config to fill in").add_argument("name")

    r = sub.add_parser("run", help="run an agent on a task set")
    r.add_argument("--agent", required=True)
    r.add_argument("--set", required=True, help="<benchmark>/<set>")
    r.add_argument("--arm", action="append", help="an arm the set lists (default: every arm it lists)")
    s = sub.add_parser("score", help="score the runs of a task set")
    s.add_argument("--set", required=True, help="<benchmark>/<set>")
    return ap


def group(argv: list[str]) -> int:
    ap = _parser()
    a = ap.parse_args(argv)
    if a.cmd is None:
        ap.print_help()
        return 0
    name = f"{a.cmd} {a.sub}" if getattr(a, "sub", None) else a.cmd
    if a.cmd == "data":
        from medomni.bench import data

        return {"connect": lambda: data.connect(a.dataset, a.path), "check": lambda: data.check(a.dataset),
                "new": lambda: data.new(a.dataset)}[a.sub]()
    part = PENDING[name]
    if name == "task check" and (a.set or a.release):
        part = CHECK_SET_PART
    print(f"medomni bench {name}: not built yet (Stage 3 part {part})", file=sys.stderr)
    return 2
