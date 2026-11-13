"""Where MIMIC-IV's files are on PhysioNet, and where this package reads them (`medomni studio download-list mimic-iv`).

The tables are downloaded whole. Chest films, ECGs and bedside waveforms are downloaded for the source population only,
the 5% hash rule. Each entry is (source, path in your copy, how): `file`, or `folder` for a folder copied whole.
"""
from __future__ import annotations

from pathlib import Path

P = "https://physionet.org/files"
CXR, ECG, WDB = f"{P}/mimic-cxr-jpg/2.1.0", f"{P}/mimic-iv-ecg/1.0", f"{P}/mimic4wdb/0.1.0"


def index_files() -> list[tuple[str, str, str]]:
    """The tables, and the record lists the rest is chosen from."""
    return [(f"{P}/mimiciv/3.1/", "core/", "folder"), (f"{P}/mimic-iv-ed/2.2/", "ed/", "folder"),
            (f"{CXR}/mimic-cxr-2.0.0-metadata.csv.gz", "cxr/mimic-cxr-2.0.0-metadata.csv.gz", "file"),
            (f"{CXR}/IMAGE_FILENAMES", "cxr/IMAGE_FILENAMES", "file"),
            (f"{ECG}/record_list.csv", "ecg/record_list.csv", "file"), (f"{WDB}/RECORDS", "wdb/RECORDS", "file")]


def _subject(path: str) -> str:
    """The subject of a record path such as `files/p10/p10000032/...`: its third part, less the `p`."""
    return path.strip("/").split("/")[2][1:]


def _lines(path: Path) -> list[str]:
    return [x for x in path.read_text(encoding="utf-8").split() if x]


def _ecg_records(path: Path) -> list[str]:
    """The record paths in MIMIC-IV-ECG's `record_list.csv` (its top `RECORDS` lists folders, not records)."""
    import csv

    with open(path, newline="", encoding="utf-8") as f:
        return [r["path"] for r in csv.DictReader(f)]


def files(raw_root: Path, params: dict, rows: dict[str, dict]) -> list[tuple[str, str, str]]:
    """Each source patient's chest films, ECGs (header and signal) and bedside waveform records."""
    raw_root, keep, out = Path(raw_root), set(rows), []
    out += [(f"{CXR}/{x}", f"cxr/{x}", "file") for x in _lines(raw_root / "cxr/IMAGE_FILENAMES") if _subject(x) in keep]
    for x in _ecg_records(raw_root / "ecg/record_list.csv"):
        if _subject(x) in keep:
            out += [(f"{ECG}/{x}{ext}", f"ecg/{x}{ext}", "file") for ext in (".hea", ".dat")]
    out += [(f"{WDB}/{x}", f"wdb/{x}", "folder") for x in _lines(raw_root / "wdb/RECORDS") if _subject(x) in keep]
    return out
