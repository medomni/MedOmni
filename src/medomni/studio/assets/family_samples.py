"""`medomni studio family-samples <family>`: write samples of a family, for real-sample checks (v0.2's `family_cuts.py`).

Files come from the event table of a connected dataset: a stable pick by hash across patients, converted through
Core's cached converters when the family needs it, cut to a window, and only then accepted: every sample must
pass Core's `conforms`. PROVENANCE.json records where each came from, so a single-vendor sample set stays visible.
The samples hold patient data; they stay in the workspace unless a dataset's licence permits publishing.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from ..tools import Assets, Result

WINDOW_SEC = 300


def cut_edf(src: Path, dst: Path, seconds: float) -> Path:
    import edfio

    edf = edfio.read_edf(src)
    if edf.duration > seconds:
        edf.slice_between_seconds(0, seconds)
    edf.write(dst)
    return dst


def cut_wfdb(src: Path, dst_stem: Path, seconds: float) -> Path:
    import wfdb

    rec = wfdb.rdrecord(str(src.with_suffix("")))
    stop = min(rec.sig_len, int(rec.fs * seconds))
    signal = rec.p_signal[:stop]
    wfdb.wrsamp(dst_stem.name, fs=rec.fs, units=rec.units, sig_name=rec.sig_name, p_signal=signal, write_dir=str(dst_stem.parent))
    return dst_stem.with_suffix(".hea")


def _copy(src: Path, dst: Path) -> list[Path]:
    """A sample and the files its format keeps beside it."""
    out = [dst]
    shutil.copyfile(src, dst)
    if src.suffix == ".hea":
        for sib in src.parent.glob(f"{src.stem}*"):
            if sib != src:
                shutil.copyfile(sib, dst.parent / sib.name.replace(src.stem, dst.stem))
                out.append(dst.parent / sib.name.replace(src.stem, dst.stem))
    return out


def sample_file(family, source: Path, tmp: Path, name: str, seconds: float) -> list[Path]:
    from medomni.core.families.check import data_format

    fmt = data_format(family)
    if fmt == "edf" and source.suffix == ".edf":
        return [cut_edf(source, tmp / f"{name}.edf", seconds)]
    if fmt == "wfdb" and source.suffix == ".hea":
        return list(tmp.glob(f"{name}.*")) if cut_wfdb(source, tmp / name, seconds) else []
    return _copy(source, tmp / f"{name}{source.suffix}")


class FamilySamples(Assets):
    name = "family-samples"
    summary = "write samples of a family, for real-sample checks"
    target = "family"

    def options(self, p) -> None:
        p.add_argument("--dataset", required=True, help="the connected dataset to cut from")
        p.add_argument("-n", type=int, default=5, help="samples to write")
        p.add_argument("--window", type=float, default=WINDOW_SEC, help="seconds kept of a long recording")

    def make(self, target, a, ctx) -> Result:
        import tempfile

        import pyarrow.compute as pc
        import pyarrow.parquet as pq

        from medomni.core import families, hashing, workspace
        from medomni.core.cache import Cache
        from medomni.core.families import converters
        from medomni.core.families.check import conforms
        from medomni.core.loading import build, find_package

        family = families.get(target)
        package = find_package(a.dataset)
        cache = Cache(Path(ctx.ws.cache))
        raw = workspace.dataset_path(ctx.ws, a.dataset)
        entry, _ = build(package, raw, cache, a.dataset)
        table = pq.read_table(entry.path / "events.parquet", columns=["subject_id", "code", "path"])
        rows = table.filter(pc.equal(table["code"], f"FILE//{target}")).to_pylist()
        if not rows:
            return Result(f"{a.dataset} has no file of family {target}", code=1)
        rows.sort(key=lambda r: hashlib.sha256(f"{target}|{r['subject_id']}|{r['path']}".encode()).hexdigest())
        found = converters.load()
        files, provenance, seen = {}, {}, set()
        with tempfile.TemporaryDirectory(prefix="medomni-samples-") as tmp:
            for r in rows:
                if len(provenance) >= a.n or r["subject_id"] in seen:  # one sample per patient
                    continue
                source = raw / r["path"]
                if source.suffix[1:] in {c.source_format for c in found.found.values()}:
                    conv = converters.for_family(target, source.suffix[1:], found)
                    e, _ = converters.cached(cache, conv, a.dataset, raw, r["path"], target, hashing.quick_id(source))
                    source = e.path / f"{target}.edf"
                name = f"sample-{len(provenance) + 1:02d}"
                made = sample_file(family, source, Path(tmp), name, a.window)
                main = next((p for p in made if p.suffix != ".dat"), None)
                if main is None or conforms(family, main):
                    continue
                seen.add(r["subject_id"])
                files.update({p.name: p.read_bytes() for p in made})
                provenance[main.name] = {"dataset": a.dataset, "path": r["path"], "family": target}
        files["PROVENANCE.json"] = json.dumps(provenance, indent=1, sort_keys=True) + "\n"
        code = 0 if len(provenance) >= min(a.n, len(rows)) or provenance else 1
        return Result(f"{target}: wrote {len(provenance)} of {a.n} requested samples from {a.dataset}", files, code)
