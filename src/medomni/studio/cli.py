"""`medomni studio`."""
from __future__ import annotations

import argparse


def group(argv: list[str]) -> int:
    from . import dummy

    parser = argparse.ArgumentParser(prog="medomni studio",
                                     description="Make tasks: survey, propose, review, preview, report.")
    sub = parser.add_subparsers(dest="cmd")
    dummy.add_parser(sub)
    try:
        a = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    if a.cmd is None:
        parser.print_help()
        return 0
    return {"dummy": dummy.run}[a.cmd](a)
