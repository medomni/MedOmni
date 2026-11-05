"""One-time converters from v0.2 content files to v0.3 contracts (R-58).

Each converter reads v0.2's files from a repository root and returns {path in v0.3 layout: data}. Nothing is
written until `write()` is called. The converted files are committed as content; the converters are deleted once
Stage 3 has used them.

    python -m medomni.core.contracts.convert families|agents|cards --repo <v0.2 root> --out <dir>

Task templates and cohorts are converted in Stage 3, with their dataset packages (R-68). Task sets,
fingerprints and result records are not converted: they are rebuilt (U2.1).
"""
from __future__ import annotations

from pathlib import Path

import yaml

NOT_CONVERTED = {
    "task-set": "task sets are rebuilt in Stage 3 under fp1: (v0.2's carry no step counts or cache hashes)",
    "fingerprint": "fingerprints are rebuilt in Stage 3 under fp1: (v0.2's use another algorithm)",
    "result-record": "result records are rebuilt in Stage 3 (v0.2's lack task_set_hash, release, fingerprint_match)",
    "task-template": "task templates are converted in Stage 3, with their dataset packages (R-68)",
}


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
