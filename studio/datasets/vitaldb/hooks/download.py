"""Where VitalDB's files are, and where this package reads them (`medomni studio download-list vitaldb`).

Sources are VitalDB's open API, which serves the tables gzip-compressed. Each entry is (source, path in your copy, how):
`file`, or `gunzip` for a file to decompress on the way.
"""
from __future__ import annotations

from pathlib import Path

API = "https://api.vitaldb.net"


def index_files() -> list[tuple[str, str, str]]:
    """The clinical, lab and track tables."""
    return [(f"{API}/cases", "clinical_info.csv", "gunzip"), (f"{API}/labs", "labs.csv", "gunzip"),
            (f"{API}/trks", "track_list.csv", "gunzip")]


def files(raw_root: Path, params: dict, rows: dict[str, dict]) -> list[tuple[str, str, str]]:
    """Each case's recording."""
    return [(f"{API}/{case}.vital", f"cases/{case}.vital", "file") for case in sorted(rows, key=int)]
