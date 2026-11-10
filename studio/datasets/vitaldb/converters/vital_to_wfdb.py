"""VitalDB's `.vital` surgery recordings into family-conformant WFDB or EDF (R-9, R-93).

Each family's tracks are written as one record `<family>.hea`/`.dat` or `<family>.edf`, resampled to the family's rate. The recording is cut
at the end of the operation, which is every VitalDB cohort's prediction time, so no signal from after it reaches a task.
Read with the `vitaldb` package. NaN gaps stay gaps (WFDB's missing-sample value); resampling is by taking every k-th
sample, so no gap spreads; capnography (62.5 to 20 Hz) and ECG (500 to 200 Hz) are interpolated.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import numpy as np

from medomni.core import families

from medomni.core.families.converters import ConvertFacts

# family -> ((track, channel name, source rate, target rate, scale), ...)
TRACKS = {
    "abp-waveform-125hz-mmhg": (("SNUADC/ART", "ART", 500, 125, 1.0), ("SNUADC/FEM", "FAP", 500, 125, 1.0)),
    # lead II alone: VitalDB records one or two leads, never the 3 to 5 the monitor family needs (Bosong, 2026-11-11)
    "ecg-1lead-200hz-uv": (("SNUADC/ECG_II", "ecg", 500, 200, 1000.0),),  # mV to uV
    "ppg-waveform-uncal": (("SNUADC/PLETH", "pleth", 500, 100, 1.0),),
    "capnography-mmhg": (("Primus/CO2", "etco2-waveform", 62.5, 20, 1.0),),
    "pressure-nonarterial-125hz-mmhg": (("SNUADC/CVP", "CVP", 500, 125, 0.735559),),  # cmH2O to mmHg
}
UNITS = {"abp-waveform-125hz-mmhg": "mmHg", "ecg-1lead-200hz-uv": "uV", "ppg-waveform-uncal": "pleth",
         "capnography-mmhg": "mmHg", "pressure-nonarterial-125hz-mmhg": "mmHg"}
MAX_DIGITAL = 32000


class ConversionError(RuntimeError):
    """This case can't be made into this family (the track is absent)."""


@lru_cache(maxsize=None)
def _op_ends(info: str) -> dict[str, float]:
    with open(info, newline="", encoding="utf-8-sig") as f:
        return {r["caseid"]: float(r["opend"]) for r in csv.DictReader(f) if r["opend"]}


def _gain(x: np.ndarray) -> tuple[float, int]:
    finite = x[np.isfinite(x)]
    lo, hi = (float(finite.min()), float(finite.max())) if finite.size else (0.0, 1.0)
    if hi <= lo:
        hi = lo + 1.0
    gain = 2 * MAX_DIGITAL / (hi - lo)
    return gain, int(round(-MAX_DIGITAL - lo * gain))


def _resample(x: np.ndarray, source: float, target: float) -> np.ndarray:
    if float(source / target).is_integer():
        return x[:: int(source / target)]
    t = np.arange(len(x)) / source
    new = np.arange(0, t[-1] if len(t) else 0, 1 / target)
    return np.interp(new, t[np.isfinite(x)], x[np.isfinite(x)]) if np.isfinite(x).any() else np.full(len(new), np.nan)


class VitalToWfdb:
    name = "vital-to-wfdb"
    version = "1"
    source_format = "vital"
    families = frozenset(TRACKS)

    def params(self, family_id: str) -> dict:
        return {"family": family_id, "tracks": [list(t) for t in TRACKS[family_id]], "cut": "opend"}

    def convert(self, src: Path, family_id: str, out: Path) -> ConvertFacts:
        import hashlib

        import vitaldb
        import wfdb

        src, out = Path(src), Path(out)
        opend = _op_ends(str(src.parent.parent / "clinical_info.csv")).get(src.stem)
        vf = vitaldb.VitalFile(str(src), [t[0] for t in TRACKS[family_id]])
        present = set(vf.get_track_names())
        chans = []
        for track, name, source, target, scale in TRACKS[family_id]:
            if track not in present:
                continue
            x = vf.to_numpy([track], 1 / source)[:, 0] * scale
            if opend is not None:
                x = x[: max(0, int(opend * source))]
            chans.append((name, _resample(x, source, target), target))
        if not chans or not any(np.isfinite(c[1]).any() for c in chans):
            raise ConversionError(f"{src.name}: no {family_id} signal")
        n = min(len(c[1]) for c in chans)
        sig = np.column_stack([c[1][:n] for c in chans])
        out.parent.mkdir(parents=True, exist_ok=True)
        if "edf" == families.get(family_id).protocol.format[0]:  # the families whose first format is EDF
            return self._edf(out, family_id, chans, sig)
        gains = [_gain(sig[:, i]) for i in range(sig.shape[1])]
        wfdb.wrsamp(out.stem, fs=chans[0][2], units=[UNITS[family_id]] * len(chans), sig_name=[c[0] for c in chans], p_signal=sig,
                    fmt=["16"] * len(chans), adc_gain=[g for g, _ in gains], baseline=[b for _, b in gains], write_dir=str(out.parent))
        hea = out.with_name(f"{out.stem}.hea")
        return ConvertFacts(hea, hashlib.sha256(hea.read_bytes()).hexdigest())


    @staticmethod
    def _edf(out: Path, family_id: str, chans, sig) -> ConvertFacts:
        """EDF has no missing-sample value, so gaps are filled by interpolation. A fixed start time keeps it deterministic."""
        import hashlib
        from datetime import datetime

        import pyedflib

        fs = int(chans[0][2])
        n = sig.shape[0] - sig.shape[0] % fs
        w = pyedflib.EdfWriter(str(out), len(chans), file_type=pyedflib.FILETYPE_EDF)
        try:
            w.setStartdatetime(datetime(2000, 1, 1))
            cols = []
            for i, (name, _, _) in enumerate(chans):
                x = sig[:n, i]
                ok = np.isfinite(x)
                x = np.interp(np.arange(n), np.flatnonzero(ok), x[ok])
                lo, hi = round(float(x.min()), 2), round(float(x.max()), 2)
                cols.append(x)
                w.setSignalHeader(i, {"label": name.upper(), "dimension": UNITS[family_id], "sample_frequency": fs,
                                      "physical_min": lo, "physical_max": hi if hi > lo else lo + 1, "digital_min": -32768,
                                      "digital_max": 32767, "prefilter": "", "transducer": ""})
            w.writeSamples(cols)
        finally:
            w.close()
        return ConvertFacts(out, hashlib.sha256(out.read_bytes()).hexdigest())


CONVERTER = VitalToWfdb()


def write_dummy(path: Path, seconds: int, rng) -> None:
    """A small `.vital` file holding every track these families read: for dummy data and tests."""
    import vitaldb

    vf = vitaldb.VitalFile()
    t0 = 1_700_000_000.0  # any fixed epoch: `.vital` times are absolute
    for tracks in TRACKS.values():
        for track, _, source, _, _ in tracks:
            n = int(seconds * source)
            vals = np.sin(np.arange(n) / source * 6.28 * 1.2) + rng.normal(0, 0.05, n)
            vf.add_track(track, [{"dt": t0, "val": vals.astype("float32")}], srate=source)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    vf.to_vital(str(path))
