"""python -m medomni.core.contracts.convert families|agents|cards|templates --repo <v0.2 root> --out <dir>

The kinds in PENDING are slots that Stage 3 parts fill; until then they exit 2 naming the part."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import PENDING, write
from . import agents, cards, families, templates


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m medomni.core.contracts.convert")
    ap.add_argument("kind", choices=["families", "agents", "cards", "templates", *PENDING])
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.kind in PENDING:
        print(f"{a.kind}: not built yet (Stage 3 part {PENDING[a.kind]})", file=sys.stderr)
        return 2
    outputs, _ = {"families": families, "agents": agents, "cards": cards, "templates": templates}[a.kind].convert(a.repo)
    written = write(outputs, a.out, templates.HEADER if a.kind == "templates" else "")
    if a.kind == "families":
        p = a.out / families.ALIAS_DEST
        p.write_text(families.aliases(a.repo), encoding="utf-8")
        written.append(p)
    print(f"wrote {len(written)} files under {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
