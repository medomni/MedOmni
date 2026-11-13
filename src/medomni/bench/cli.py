"""`medomni bench`.

Every command the CLI page lists has a slot here.
"""
from __future__ import annotations

import argparse
import sys

def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="medomni bench", description="Run agents on built task sets and score them.")
    sub = ap.add_subparsers(dest="cmd", metavar="<command>")

    data = sub.add_parser("data", help="record where your copy of a dataset is")
    dsub = data.add_subparsers(dest="sub", metavar="<data command>", required=True)
    c = dsub.add_parser("connect", help="record where your copy of a dataset is")
    c.add_argument("dataset")
    c.add_argument("--path", required=True)

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

        return data.connect(a.dataset, a.path)
    if a.cmd in ("run", "score"):
        from medomni.bench import runs
        from medomni.core.tasks import TaskError as BuildError

        try:
            if a.cmd == "score":
                return runs.score(a.set)
            runs.run(a.set, a.agent, a.arm)
            return 0
        except (BuildError, RuntimeError, LookupError, FileNotFoundError) as e:
            print(e, file=sys.stderr)
            return 1
    if a.cmd == "agent":
        from medomni.bench import agent

        return agent.new_agent(a.name)
