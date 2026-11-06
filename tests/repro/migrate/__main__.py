"""python -m medomni.core.contracts.convert families|agents|cards --repo <v0.2 root> --out <dir>"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import write
from . import agents, cards, families


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m medomni.core.contracts.convert")
    ap.add_argument("kind", choices=["families", "agents", "cards"])
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    outputs, _ = {"families": families, "agents": agents, "cards": cards}[a.kind].convert(a.repo)
    written = write(outputs, a.out)
    if a.kind == "families":
        p = a.out / families.ALIAS_DEST
        p.write_text(families.aliases(a.repo), encoding="utf-8")
        written.append(p)
    print(f"wrote {len(written)} files under {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
