"""`medomni perception`."""
from __future__ import annotations

import argparse


def group(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="medomni perception", description="Pull and run encoders; the gateway. No commands yet.")
    parser.parse_args(argv)
    parser.print_help()
    return 0
