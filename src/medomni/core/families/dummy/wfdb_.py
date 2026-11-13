"""WFDB records (format 16) from the family file."""
from __future__ import annotations

from pathlib import Path

from . import SECONDS, channel_names, rate, rng
from .signal import _span

ROLES_PER_RECORD = {"abp-waveform-125hz-mmhg": 1}  # roles one record carries; default 3. ABP: one arterial channel


def _format_level(family, seed, names, fs):
    import numpy as np

    lo, hi = _span(family)
    n = int(round(fs * SECONDS))
    g = rng(seed, family.id)
    t = np.arange(n) / fs
    mid, half = (lo + hi) / 2, (hi - lo) / 2
    return np.column_stack([mid + half * 0.8 * np.clip(0.6 * np.sin(2 * np.pi * g.uniform(0.2, 2) * t)
                                                       + 0.3 * g.standard_normal(n), -1, 1) for _ in names])


def write(family, seed: int, path: Path, *, subject: str, start, level: str = "format") -> None:
    import numpy as np
    import wfdb

    fs = rate(family)
    names = channel_names(family, ROLES_PER_RECORD.get(family.id, 3))
    sig = None
    if level == "physiology":
        from . import physio
        from .subject import subject as subject_model

        s = subject_model(seed, subject)
        seconds = physio.duration(len(names), fs)
        xs = [physio.signal(family, name, s, fs, seconds, seed) for name in names]
        if all(x is not None for x in xs):
            sig = np.column_stack(xs)
    if sig is None:
        sig = _format_level(family, seed, names, fs)
    unit = family.protocol.units if family.protocol.units not in (None, "per-channel") else "NU"
    wfdb.wrsamp(path.stem, fs=fs, units=[unit] * len(names), sig_name=names, p_signal=sig, fmt=["16"] * len(names),
                write_dir=str(path.parent), base_date=start.date(), base_time=start.time(),
                comments=[f"subject: {subject}"])
