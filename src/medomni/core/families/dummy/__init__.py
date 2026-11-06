"""Dummy data at the format level (part 5; R-70 to R-75).

`make_dummy(family, seed, out_dir)` writes one file that passes `families.check.conforms` for that family: the right
format, channels, rate, units, dtype, range, dimensions and planes. Values are seeded, not physiological (that is
part 5b). It reads the family file and the seed only: no dataset, no network.

    from medomni.core import families
    from medomni.core.families.dummy import make_dummy
    path = make_dummy(families.get("spo2-series-10hz-pct"), seed=1, out_dir=tmp)
"""
from __future__ import annotations

import zlib
from datetime import datetime
from pathlib import Path

from ..check import data_format

# U2.12: four families declare no rate. Dummies use this rate, for tests only; it is not a protocol value.
TEST_RATES = {"capnography-mmhg": 100.0, "ppg-waveform-uncal": 100.0, "resp-flow": 100.0, "snore-acoustic": 100.0}
START = datetime(2150, 1, 1, 0, 0, 0)  # an invented date, far from any real recording
SECONDS = 30  # signal length


def rng(seed: int, *keys: str):
    import numpy as np

    return np.random.default_rng([seed, *(zlib.crc32(k.encode()) for k in keys)])


def rate(family) -> float:
    r = family.protocol.rate_hz or TEST_RATES.get(family.id)
    if r is None:
        raise ValueError(f"{family.id}: no rate declared and no test rate (U2.12)")
    return float(r)


def channel_names(family, k_roles: int | None = None) -> list[str]:
    """The channel labels a dummy carries: declared channels, generated names for a count, or the roles."""
    p = family.protocol
    if isinstance(p.channels, tuple):
        return list(p.channels)
    if isinstance(p.channels, int):
        return [f"ch{i + 1}" for i in range(p.channels)]
    if p.roles:
        return list(p.roles[:k_roles] if k_roles else p.roles)
    raise ValueError(f"{family.id}: no channels or roles to generate")


EXTENSIONS = {"edf": ".edf", "wfdb": ".hea", "dicom": ".dcm", "image": ".png", "omh": ".json", "table": ".csv"}


def make_dummy(family, seed: int, out_dir: str | Path, name: str | None = None, *, subject: str = "DUMMY-1",
               start: datetime = START) -> Path:
    """Write a dummy file for `family` into `out_dir` and return its path (a WFDB record returns its `.hea`)."""
    from . import dicom, omh, signal, table, wfdb_

    fmt = data_format(family)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name or family.id}{EXTENSIONS[fmt]}"
    writer = {"edf": signal.write_edf, "wfdb": wfdb_.write, "dicom": dicom.write_dicom, "image": dicom.write_png,
              "omh": omh.write, "table": table.write}[fmt]
    writer(family, seed, path, subject=subject, start=start)
    return path
