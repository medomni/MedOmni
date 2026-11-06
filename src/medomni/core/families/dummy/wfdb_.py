"""WFDB records (format 16) from the family file."""
from __future__ import annotations

from pathlib import Path

from . import SECONDS, channel_names, rate, rng
from .signal import _span

ROLES_PER_RECORD = 3  # a record carries a few of a family's roles


def write(family, seed: int, path: Path, *, subject: str, start) -> None:
    import numpy as np
    import wfdb

    fs = rate(family)
    names = channel_names(family, ROLES_PER_RECORD)
    lo, hi = _span(family)
    n = int(round(fs * SECONDS))
    g = rng(seed, family.id)
    t = np.arange(n) / fs
    mid, half = (lo + hi) / 2, (hi - lo) / 2
    sig = np.column_stack([mid + half * 0.8 * np.clip(0.6 * np.sin(2 * np.pi * g.uniform(0.2, 2) * t)
                                                       + 0.3 * g.standard_normal(n), -1, 1) for _ in names])
    unit = family.protocol.units if family.protocol.units not in (None, "per-channel") else "NU"
    wfdb.wrsamp(path.stem, fs=fs, units=[unit] * len(names), sig_name=names, p_signal=sig, fmt=["16"] * len(names),
                write_dir=str(path.parent), base_date=start.date(), base_time=start.time(),
                comments=[f"subject: {subject}"])
