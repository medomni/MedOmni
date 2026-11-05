"""`medomni studio`."""
from __future__ import annotations

import argparse


def group(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="medomni studio", description="Make tasks: survey, propose, review, preview, report. No commands yet.")
    parser.parse_args(argv)
    parser.print_help()
    return 0
