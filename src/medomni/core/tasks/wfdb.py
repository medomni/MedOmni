"""A WFDB record's companion files, read from its header: what staging must copy and the recordings check expects."""
from __future__ import annotations

from pathlib import Path


def signal_lines(hea: Path):
    lines = [ln.split() for ln in hea.read_text(errors="replace").splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    return (lines[0], lines[1:]) if lines else ([], [])


def companions(hea: Path) -> list[Path]:
    """The files a WFDB header names, read from the header (segment signal names are not a stem glob). A
    multi-segment master header names segment headers, followed in turn."""
    rec, sigs = signal_lines(hea)
    out: list[Path] = []
    if rec and "/" in rec[0]:
        for sg in sigs:
            if sg and sg[0] != "~":
                seg = hea.parent / f"{sg[0]}.hea"
                if seg.exists():
                    out += [seg, *companions(seg)]
        return out
    for name in dict.fromkeys(sg[0] for sg in sigs if sg and sg[0] != "-"):
        f = hea.parent / name
        if not f.exists():
            raise RuntimeError(f"WFDB header {hea.name} names a missing signal file {name}")
        out.append(f)
    return out
