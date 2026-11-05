"""`medomni bench`."""
from __future__ import annotations

import argparse


def group(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="medomni bench", description="Build tasks, run agents and score them. No commands yet.")
    parser.parse_args(argv)
    parser.print_help()
    return 0
