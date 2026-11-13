"""MIMIC-IV bedside waveforms and numerics: one `FILE//<family>` row per segment and family, one per numerics file.

Why a hook: a record's start time is in its master header, each segment's time is the record start plus the samples
before it, and a segment's families come from the signals its own header lists. The rules are v0.2's
(its MIMIC adapter's `mimic_wdb_in_window` and `_WDB_FAM`, and its manifest catalog), unchanged.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

FAMILIES = (({"ABP", "ART", "AO", "FAP", "UAP"}, "abp-waveform-125hz-mmhg"),
            ({"ICP", "CVP", "PAP"}, "pressure-nonarterial-125hz-mmhg"),
            ({"II", "V", "AVR", "I", "III", "MCL", "MCL1"}, "ecg-monitor-3to5lead-250hz-continuous"),
            ({"RESP"}, "resp-impedance-62hz-ohm"),
            ({"PLETH"}, "ppg-waveform-uncal"))


def _dirs(path: Path) -> list[Path]:
    return sorted(Path(e.path) for e in os.scandir(path) if e.is_dir())


def records(root: Path):
    """(subject, record folder) for every record on disk."""
    if not root.is_dir():
        return
    for group in _dirs(root):
        for patient in _dirs(group):
            for rec in _dirs(patient):
                yield patient.name[1:], rec


def _segments(rec: Path):
    """(segment, start time) for every segment of a record with a readable master header."""
    master = rec / f"{rec.name}.hea"
    if not master.exists():
        return
    lines = master.read_text().splitlines()
    head = lines[1].split() if lines and lines[0].startswith("#") else lines[0].split()
    try:
        fs = float(head[2].split("/")[0])
        base = datetime.strptime(f"{head[5]} {head[4].split('.')[0]}", "%d/%m/%Y %H:%M:%S")
    except (IndexError, ValueError):
        return
    off = 0
    for line in lines:
        toks = line.split()
        if len(toks) != 2 or not toks[1].isdigit():
            continue
        seg, nsamp = toks[0], int(toks[1])
        start = base + timedelta(seconds=off / fs)
        off += nsamp
        if not seg.endswith("_0000") and nsamp != 0:
            yield seg, start


def derive(rows, raw_root: Path, params: dict) -> list[dict]:
    root = Path(raw_root) / params["root"]
    out = []
    for s, rec in records(root):
        rel = rec.relative_to(raw_root).as_posix()
        for seg, start in _segments(rec):
            hea = rec / f"{seg}.hea"
            if not hea.exists():
                continue
            names = {ln.split()[-1].upper() for ln in hea.read_text().splitlines()[1:] if ln.strip() and not ln.startswith("#")}
            for sigs, fam in FAMILIES:
                if sigs & names:
                    out.append({"subject_id": s, "time": str(start)[:19].replace(" ", "T"), "code": f"FILE//{fam}", "path": f"{rel}/{seg}.hea"})
        numerics = rec / f"{rec.name}n.csv.gz"
        if numerics.exists():
            out.append({"subject_id": s, "time": None, "code": "FILE//numeric-observation", "path": f"{rel}/{numerics.name}"})
    return out


def inputs(raw_root: Path, params: dict) -> list[str]:
    root = Path(raw_root) / params["root"]
    return [(rec / f"{rec.name}.hea").relative_to(raw_root).as_posix() for _, rec in records(root) if (rec / f"{rec.name}.hea").exists()]
