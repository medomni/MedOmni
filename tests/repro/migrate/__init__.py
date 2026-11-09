"""One-time converters from v0.2 content files to v0.3 contracts (R-58).

Each converter reads v0.2's files from a repository root and returns {path in v0.3 layout: data}. Nothing is
written until `write()` is called. The converted files are committed as content; the converters are deleted once
Stage 3 has used them.

    python -m medomni.core.contracts.convert families|agents|cards|templates --repo <v0.2 root> --out <dir>

Task templates and their cohorts are converted in Stage 3 part 2, into their dataset packages (`templates`, R-68);
imported v0.2 result records in Stage 3 part 5. Task sets are not converted: they are rebuilt (U2.1). v0.2's fingerprints have no v0.3
counterpart (R-111).
"""
from __future__ import annotations

from pathlib import Path

import yaml

NOT_CONVERTED = {
    "task-set": "task sets are rebuilt in Stage 3 part 4: v0.3 sets pin pairs at a version (R-108)",
    "result-record": "v0.2 result records are imported in Stage 3 part 5, at version 0 with a v0.2: stand-in (R-90)",
}

# Converters Stage 3 adds, and the part that fills each slot
PENDING = {"benchmarks": 4, "result-records": 5}


class NotConverted(ValueError):
    pass


def refuse(kind: str) -> None:
    raise NotConverted(NOT_CONVERTED[kind])


def dump(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120, default_flow_style=None)


def write(outputs: dict[str, dict], out: Path, header: str = "") -> list[Path]:
    written = []
    for rel, data in sorted(outputs.items()):
        p = Path(out) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(header + dump(data), encoding="utf-8")
        written.append(p)
    return written
