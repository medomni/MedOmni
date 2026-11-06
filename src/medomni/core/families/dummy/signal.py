"""EDF signals from the family file, and the h5 night files the bridge reads (BDSP shape)."""
from __future__ import annotations

from pathlib import Path

from . import SECONDS, channel_names, rate, rng

# Physical span by unit, for families that declare no range
SPAN = {"uv": (-500.0, 500.0), "mv": (-5.0, 5.0), "mmhg": (0.0, 300.0), "bpm": (0.0, 250.0), "%": (0.0, 100.0),
        "ohm": (0.0, 2000.0), "mg/dl": (20.0, 600.0)}
DEFAULT_SPAN = (-1000.0, 1000.0)
DIG = (-32768, 32767)
CONCRETE = lambda u: u not in (None, "per-channel", "per-transducer", "per-member", "mixed")  # noqa: E731


def _span(family) -> tuple[float, float]:
    p = family.protocol
    if p.range is not None:
        return float(p.range[0]), float(p.range[1])
    return SPAN.get((p.units or "").lower(), DEFAULT_SPAN)


def _digital(family, seed: int, name: str, n: int, fs: float):
    """Seeded int16 samples: a slow wave plus noise, inside 90% of the digital range."""
    import numpy as np

    g = rng(seed, family.id, name)
    if family.protocol.categorical:
        return np.repeat(g.integers(0, 5, size=max(1, n // int(fs * 5) + 1)), int(fs * 5))[:n].astype(np.int16)
    t = np.arange(n) / fs
    x = 0.6 * np.sin(2 * np.pi * g.uniform(0.2, 2.0) * t + g.uniform(0, 6.28)) + 0.3 * g.standard_normal(n)
    return (np.clip(x, -1, 1) * 0.9 * DIG[1]).astype(np.int16)


def _header_number(v: float) -> float:
    """EDF header fields hold 8 characters."""
    return round(v, 1) if abs(v) >= 1000 else round(v, 3)


def _to_digital(x, lo: float, hi: float, dig: tuple[int, int]):
    import numpy as np

    d = np.round((np.clip(x, lo, hi) - lo) / (hi - lo) * (dig[1] - dig[0]) + dig[0])
    return np.clip(d, *dig).astype(np.int16)


def _physical_span(family, x) -> tuple[float, float]:
    p = family.protocol
    if p.range is not None:
        return float(p.range[0]), float(p.range[1])
    lo, hi = float(x.min()), float(x.max())
    pad = max(0.1 * (hi - lo), 1e-3)
    return _header_number(lo - pad), _header_number(hi + pad)


def channels(family, seed: int, *, level: str = "format", subject: str = "DUMMY-1", seconds: float | None = None):
    """[(label, fs, unit, (phys_min, phys_max), (dig_min, dig_max), int16 samples)] for one family."""
    fs = rate(family)
    names = channel_names(family)
    unit = family.protocol.units if CONCRETE(family.protocol.units) else ""
    out = []
    if level == "physiology":
        from . import physio
        from .subject import subject as subject_model

        seconds = seconds or physio.duration(len(names), fs)
        s = subject_model(seed, subject)
        for name in names:
            x = physio.signal(family, name, s, fs, seconds, seed)
            if x is None:
                break
            if family.protocol.categorical:
                out.append((name, fs, unit, (0.0, 7.0), (0, 7), x.astype("int16")))
                continue
            lo, hi = _physical_span(family, x)
            out.append((name, fs, unit, (lo, hi), DIG, _to_digital(x, lo, hi, DIG)))
        else:
            return out
        out = []  # a family with no physiology generator stays at the format level
    lo, hi = _span(family)
    dig = DIG
    if family.protocol.categorical:
        lo, hi, dig = 0.0, 7.0, (0, 7)
    for name in names:
        n = int(round(fs * SECONDS))
        out.append((name, fs, unit, (lo, hi), dig, _digital(family, seed, name, n, fs)))
    return out


def write_edf(family, seed: int, path: Path, *, subject: str, start, level: str = "format") -> None:
    import pyedflib

    chans = channels(family, seed, level=level, subject=subject)
    w = pyedflib.EdfWriter(str(path), len(chans), file_type=pyedflib.FILETYPE_EDF)
    try:
        w.setStartdatetime(start)
        w.setPatientCode(subject)
        w.setSignalHeaders([{"label": name, "dimension": unit, "sample_frequency": fs,
                             "physical_min": phys[0], "physical_max": phys[1],
                             "digital_min": dig[0], "digital_max": dig[1], "prefilter": "", "transducer": ""}
                            for name, fs, unit, phys, dig, _ in chans])
        w.writeSamples([data.astype("int32") for *_, data in chans], digital=True)
    finally:
        w.close()


def write_h5(families: list, seed: int, path: Path, *, subject: str, start, level: str = "physiology") -> None:
    """One night in the h5 layout v0.2's bridge reads: `signals/<name>` int16 datasets with fs, unit, phys and dig
    attributes. Channel names are the families' channels, or their roles lowercased, as the bridge looks them up."""
    import h5py

    from . import physio

    # one night holds every family's channels, so its length is set by all of them together (under 1 MiB)
    rates = [rate(f) for f in families for _ in channel_names(f)]
    seconds = physio.duration(1, sum(rates))
    seen = {}
    for family in families:
        for name, fs, unit, phys, dig, data in channels(family, seed, level=level, subject=subject, seconds=seconds):
            key = name if isinstance(family.protocol.channels, tuple) else name.lower()
            seen.setdefault(key, (fs, unit, phys, dig, data))
    with h5py.File(path, "w") as f:
        f.attrs["meas_date"] = start.strftime("%Y-%m-%d %H:%M:%S")
        f.attrs["subject"] = subject
        g = f.create_group("signals")
        for key in sorted(seen):
            fs, unit, phys, dig, data = seen[key]
            d = g.create_dataset(key, data=data)
            d.attrs.update({"fs": fs, "unit": unit, "phys_min": phys[0], "phys_max": phys[1],
                            "dig_min": dig[0], "dig_max": dig[1]})
