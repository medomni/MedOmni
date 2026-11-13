"""One-time converters from v0.2 content files to v0.3 contracts (R-58).

Each converter reads v0.2's files from a v0.2.1 tree (`v02_tree`, out of git history since Stage 3 part 8) and returns {path in v0.3 layout: data}. Nothing is
written until `write()` is called. The converted files are committed as content. These converters ship with nothing:
they live with the reproduction tests, frozen after v0.3 (R-145).

    python -m tests.repro.migrate families|agents|cards|templates --repo <v0.2 root> --out <dir>

Task templates and their cohorts are converted in Stage 3 part 2, into their dataset packages (`templates`, R-68);
imported v0.2 result records in Stage 3 part 5. Task sets are not converted: they are rebuilt (U2.1). v0.2's fingerprints have no v0.3
counterpart (R-111).
"""
from __future__ import annotations

from pathlib import Path

import io
import subprocess
import tarfile

import yaml

V02_COMMIT = "aa45b68"  # v0.2.1; its files left the tree in Stage 3 part 8 and are read from history
V02_PATHS = ("data_task", "harness/harbor/agents", "harness/experiments", "harness/models.yaml", "perception/runtime")


def v02_tree(repo: Path, dest: Path, paths=V02_PATHS) -> Path:
    """Write v0.2.1's files under `paths` from `repo`'s git history into `dest`; returns `dest`."""
    out = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", V02_COMMIT, "--", *paths],
                         capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(out)) as tar:
        tar.extractall(dest)
    return Path(dest)

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
