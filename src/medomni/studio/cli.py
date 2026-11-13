"""`medomni studio`: `task` and `data` (building tasks, R-142), every tool's command, found through `tools.found()`, and
`check <tool>`."""
from __future__ import annotations

import argparse
import sys


def _parser(loaded: dict) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="medomni studio", description="Build tasks, and the tools around them: survey, "
                                 "propose, review, preview, report, assets.")
    sub = ap.add_subparsers(dest="cmd", metavar="<command>")
    task = sub.add_parser("task", help="write, build and check tasks")
    tsub = task.add_subparsers(dest="sub", metavar="<task command>", required=True)
    n = tsub.add_parser("new", help="write a task template and an n20 cohort to fill in")
    n.add_argument("template")
    n.add_argument("--dataset", required=True)
    b = tsub.add_parser("build", help="build a pair, or rebuild a published set with the builder it names")
    b.add_argument("pair", nargs="?", help="<template>@<cohort>")
    b.add_argument("--set", help="<benchmark>/<set>")
    b.add_argument("--arm", action="append", help="an arm the set lists (default: every arm it lists)")
    k = tsub.add_parser("check", help="check a pair, every pair a set pins, or every pinned pair for a release")
    k.add_argument("pair", nargs="?", help="<template>@<cohort>")
    k.add_argument("--set", help="<benchmark>/<set>")
    k.add_argument("--release", action="store_true", help="every pinned pair in every set (MedOmni releases)")
    data = sub.add_parser("data", help="check your copy of a dataset against its package; write a new dataset package")
    dsub = data.add_subparsers(dest="sub", metavar="<data command>", required=True)
    dsub.add_parser("check", help="check your copy against its dataset package").add_argument("dataset")
    dsub.add_parser("new", help="write a dataset package to fill in").add_argument("dataset")
    for name, tool in sorted(loaded.items()):
        p = sub.add_parser(name, help=tool.summary, description=tool.summary)
        if tool.target:
            p.add_argument("target", metavar=tool.target, help=tool.target_help or None)
        p.add_argument("--out", help="write here instead of the tool's folder in the workspace")
        tool.options(p)
    c = sub.add_parser("check", help="check a tool against its kind's interface")
    c.add_argument("tool", metavar="<tool>")
    return ap


def group(argv: list[str]) -> int:
    from medomni.core import plugins
    from medomni.core.contracts import ContractError
    from medomni.core.workspace import WorkspaceError

    from . import tools

    found = tools.found()
    loaded, errors = {}, list(found.errors)
    for name, target in found.targets.items():
        try:
            loaded[name] = tools.load(target, name)
        except plugins.PluginError as e:
            errors.append(str(e))
    ap = _parser(loaded)
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    if a.cmd is None:
        ap.print_help()
        return 0
    if a.cmd == "check":
        return _check(a.tool, found, loaded, errors)
    if a.cmd == "task":
        from . import task

        return {"new": lambda: task.new(a.template, a.dataset), "build": lambda: task.build(a.pair, a.set, a.arm),
                "check": lambda: task.check(a.pair, a.set, a.release)}[a.sub]()
    if a.cmd == "data":
        from . import data

        return {"check": lambda: data.check(a.dataset), "new": lambda: data.new(a.dataset)}[a.sub]()
    for e in errors:
        print(f"medomni studio: {e}", file=sys.stderr)
    try:
        return loaded[a.cmd].run(a, tools.Context())
    except (tools.ToolError, WorkspaceError, ContractError) as e:
        print(f"medomni studio {a.cmd}: {e}", file=sys.stderr)
        return 2


def _check(name: str, found, loaded: dict, errors: list[str]) -> int:
    from . import tools

    if name not in loaded:
        print(f"no tool '{name}' ({', '.join(sorted(loaded))})" if name not in found.targets else
              f"{name}: cannot be loaded: {next((e for e in errors if found.targets[name] in e), errors)}", file=sys.stderr)
        return 1
    problems = tools.problems(loaded[name], name)
    for p in problems:
        print(f"  {name}: {p}")
    print(f"{name}: {'ok' if not problems else f'{len(problems)} problem(s)'} ({loaded[name].kind})")
    return 1 if problems else 0
