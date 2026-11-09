"""The `h5-to-edf` family converter: a BDSP night (`.h5`) into one family's EDF (R-19, R-105, R-110).

v0.2's bridge (`data_task/familybridge/bridge.py`), as a Core family converter. The conversion is unchanged: the
family's protocol channels (or roles) are looked up among the night's signals by v0.2's rule, and copied bit for bit
as int16, cut to whole seconds, with no annotations and no subject header fields (they can carry gold).

Two things differ from v0.2:

- The cache key (R-86) hashes only what the conversion reads: the protocol's `channels` and `roles`, and each
  accepted alias block's `channels`, `roles` and `prefixes`. Rate, units, dtype and range can change without a new
  key. `params(family_id)` gives the dict that goes into Core's cache key.
- A night with no `meas_date` gets a fixed start time instead of the wall clock, so the same input always gives the
  same bytes (converters.py). v0.2 wrote the conversion time there: 27 of its cached entries carry it (p09).

Channel names are matched as written in the h5 file, so `core/families/aliases.yaml` and the family files are read
as raw YAML in file order, not through the alias resolver, which normalises labels (p06).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from functools import cache
from pathlib import Path

import yaml

from . import ALIASES, folder
from .converters import ConvertFacts

FIXED_START = datetime(1985, 1, 1)  # EDF's earliest date; only for a night that names no start time

# The families v0.2's bridge converted (the 14 with live cache entries, p06)
FAMILIES = frozenset({
    "body-position-code-10hz", "capnography-mmhg", "ecg-1lead-200hz-uv", "eeg-sleep-6ch-200hz-uv",
    "emg-chin-200hz-uv", "emg-limb-200hz-uv", "eog-2ch-200hz-uv", "ppg-waveform-uncal",
    "psg-cardiorespiratory-4ch-200hz-mixed", "pulse-rate-10hz-bpm", "resp-effort-rip-2ch-50hz", "resp-flow",
    "snore-acoustic", "spo2-series-10hz-pct",
})


class Absent(RuntimeError):
    """The night has no signal for one of the family's required channels, or for any of its roles."""


@cache
def _raw(d: Path) -> tuple[dict, dict]:
    protocols = {}
    for p in sorted(d.glob("*.yaml")):
        if p.name != ALIASES:
            protocols[p.stem] = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("protocol", {})
    alias = yaml.safe_load((d / ALIASES).read_text(encoding="utf-8")) or {}
    return protocols, alias


def _accepts(family_id: str, alias: dict) -> list[dict]:
    out = []
    for acc in (alias.get("families", {}).get(family_id) or {}).get("accepts", []):
        out.append(alias.get("vocab", {}).get(acc, {}) if isinstance(acc, str) else acc)
    return out


def reads(family_id: str, root: Path | None = None) -> dict:
    """What the conversion of this family reads, and nothing else (R-86)."""
    protocols, alias = _raw(folder(root).resolve())
    proto = protocols[family_id]
    accepts = [{k: entry.get(k) for k in ("channels", "roles", "prefixes")} for entry in _accepts(family_id, alias)]
    return {"channels": proto.get("channels"), "roles": proto.get("roles"),
            "accepts": [a for a in accepts if any(a.values())]}  # a block that only adds rates is not read


def _channel_sources(family_id: str, proto: dict, alias: dict):
    """[(canonical label, [candidate supply names], required)]: channels exact, roles as vocabulary (v0.2's rule)."""
    maps, prefixes, role_maps = {}, [], {}
    for entry in _accepts(family_id, alias):
        maps.update(entry.get("channels", {}))
        prefixes += entry.get("prefixes", [])
        for srcname, tgt in entry.get("roles", {}).items():
            role_maps.setdefault(str(tgt).lower(), []).append(srcname)
        for srcname, tgt in entry.get("channels", {}).items():
            role_maps.setdefault(str(tgt).lower(), []).append(srcname)
    if proto.get("channels"):
        out = []
        for canon in proto["channels"]:
            cands = [canon] + sorted(s for s, t in maps.items() if t == canon)
            out.append((canon, cands + [p + c for p in prefixes for c in cands], True))
        return out
    return [(r, [str(r).lower()] + role_maps.get(str(r).lower(), []), False) for r in proto.get("roles", [])]


def available(signals, family_id: str, root: Path | None = None) -> bool:
    """Whether a night whose h5 `signals` group holds these names supplies the family, by the conversion's own
    rule (every required channel, or at least one role), without converting it."""
    protocols, alias = _raw(folder(root).resolve())
    names = set(signals)
    found = [(required, any(c in names for c in cands))
             for _, cands, required in _channel_sources(family_id, protocols[family_id], alias)]
    return bool(found) and all(ok for req, ok in found if req) and any(ok for _, ok in found)


def h5_to_family_edf(src: Path, dest: Path, family_id: str, proto: dict, alias: dict) -> None:
    """A family-conformant EDF: protocol channels only, int16 copied bit for bit, whole seconds."""
    import h5py
    import numpy as np
    import pyedflib

    chans = []
    with h5py.File(src) as f:
        sig = f["signals"]
        for canon, cands, required in _channel_sources(family_id, proto, alias):
            name = next((c for c in cands if c in sig), None)
            if name is None:
                if not required:
                    continue
                raise Absent(f"{Path(src).name}: no supply for {family_id}:{canon!r}")
            d = sig[name]
            fs = int(d.attrs["fs"])
            if fs != d.attrs["fs"] or fs <= 0:
                raise Absent(f"{Path(src).name}/{name}: non-integer rate {d.attrs['fs']}")
            chans.append({"label": str(canon).upper(), "fs": fs, "unit": str(d.attrs.get("unit", "")),
                          "phys": (round(float(d.attrs["phys_min"]), 2), round(float(d.attrs["phys_max"]), 2)),
                          "dig": (max(-32768, int(d.attrs["dig_min"])), min(32767, int(d.attrs["dig_max"]))),
                          "data": np.asarray(d[...], dtype=np.int32)})
        start = str(f.attrs.get("meas_date", ""))[:19]
    if not chans:
        raise Absent(f"{Path(src).name}: no role supply at all for {family_id}")
    seconds = min(len(c["data"]) // c["fs"] for c in chans)
    w = pyedflib.EdfWriter(str(dest), len(chans), file_type=pyedflib.FILETYPE_EDF)
    try:
        w.setStartdatetime(datetime.strptime(start, "%Y-%m-%d %H:%M:%S") if start else FIXED_START)
        w.setSignalHeaders([{"label": c["label"], "dimension": c["unit"], "sample_frequency": c["fs"],
                             "physical_min": c["phys"][0], "physical_max": c["phys"][1],
                             "digital_min": c["dig"][0], "digital_max": c["dig"][1],
                             "prefilter": "", "transducer": ""} for c in chans])
        w.writeSamples([np.clip(c["data"][: seconds * c["fs"]], *c["dig"]) for c in chans], digital=True)
    finally:
        w.close()


class H5ToEdf:
    name = "h5-to-edf"
    version = "1"
    source_format = "h5"
    families = FAMILIES

    def __init__(self, root: Path | None = None):
        self.root = root

    def params(self, family_id: str) -> dict:
        """The cache key's params for one family: the family, and a hash of what its conversion reads (R-86)."""
        doc = json.dumps(reads(family_id, self.root), sort_keys=True)
        return {"family": family_id, "reads": hashlib.sha256(doc.encode()).hexdigest()}

    def convert(self, src: Path, family, out: Path) -> ConvertFacts:
        fid = family if isinstance(family, str) else family.id
        if fid not in self.families:
            raise ValueError(f"h5-to-edf does not convert {fid}")
        protocols, alias = _raw(folder(self.root).resolve())
        h5_to_family_edf(Path(src), Path(out), fid, protocols[fid], alias)
        return ConvertFacts(Path(out), hashlib.sha256(Path(out).read_bytes()).hexdigest())


CONVERTER = H5ToEdf()
