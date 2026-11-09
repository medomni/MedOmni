"""The audit's Family cells, from v0.2's `family_audit.py`: the registry, and `--samples` against the families' checks.

The HuggingFace sample store is not read here (no network in an audit): pass a sample folder, such as one written by
`medomni studio family-samples`. The store's upload, prune and re-provenance commands are not rebuilt.
"""
from __future__ import annotations

import json
from pathlib import Path

from medomni.core import hashing

from ..matrix import FAIL, NONE, PASS, WARN

SIGNAL_FORMATS = {"edf", "wfdb"}
MIN_SAMPLES = 3


def run(scope, sink) -> None:
    from medomni.core.families.check import data_format

    targets = _target_names()
    for fid, fam in scope.families.items():
        p = fam.protocol
        fmt = data_format(fam)
        undeclared = [] if fmt not in SIGNAL_FORMATS else [k for k in ("rate_hz", "units") if getattr(p, k) in (None, "")]
        sink.add("F-COMP.1", "M", fid, WARN if undeclared else PASS, f"undeclared: {undeclared}" if undeclared else "protocol declared", "family file")
        sink.add("F-COMP.2", "M", fid, PASS if fam.samples else WARN, "samples pinned" if fam.samples else "no samples pinned", "family file")
        hits = [t for t in targets if t in fid.lower()]
        sink.add("F-ISOL.2", "M", fid, FAIL if hits else PASS, f"family id names target(s) {hits}" if hits else "family id names no target", "family file")
        if scope.samples is None:
            sink.add("F-CONF.1", "M", fid, NONE, "no sample folder given (--samples)", "audit")
            continue
        _samples(scope.samples / fid, fid, fam, sink, targets)


def _samples(folder: Path, fid: str, fam, sink, targets: set[str]) -> None:
    from medomni.core.families.check import conforms

    if not folder.is_dir():
        sink.add("F-CONF.1", "M", fid, NONE, "no samples for this family in the folder", "audit")
        return
    files = sorted(f for f in folder.iterdir() if f.is_file() and f.suffix != ".dat" and f.name not in ("manifest.jsonl", "PROVENANCE.json"))
    if len(files) < MIN_SAMPLES:
        sink.add("F-COMP.2", "M", fid, WARN, f"only {len(files)} sample(s)", "samples")
    manifest = folder / "manifest.jsonl"
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            m = json.loads(line) if line.strip() else None
            if m and (folder / m["file"]).exists() and m.get("sha256") and m["sha256"] != hashing.sha256_file(folder / m["file"]):
                sink.add("F-COMP.2", "M", fid, FAIL, f"manifest sha256 mismatch for {m['file']}", "samples")
    for f in files:
        probs = conforms(fam, f)
        sink.add("F-CONF.1", "M", f"{fid}/{f.name}", FAIL if probs else PASS, "; ".join(probs)[:400] or "conforms", "conforms")
        sink.add("F-CONF.2", "M", f"{fid}/{f.name}", FAIL if probs else PASS, "; ".join(probs)[:400] or "conforms", "conforms")
        hits = [t for t in targets if t in f.name.lower()]
        sink.add("F-ISOL.2", "M", f"{fid}/{f.name}", FAIL if hits else PASS, f"sample name holds target(s) {hits}" if hits else "sample name holds no target", "sample names")


def _target_names() -> set[str]:
    """Every template target's name of 4 or more letters, read from the repository's packages."""
    import yaml

    from medomni.core import plugins

    out: set[str] = set()
    repo = plugins.find_repo()
    if repo is None:
        return out
    for tp in (repo / "bench/datasets").glob("*/tasks/*/template.yaml"):
        for t in (yaml.safe_load(tp.read_text(encoding="utf-8")) or {}).get("targets", []):
            if len(str(t.get("name", ""))) > 3:
                out.add(str(t["name"]).lower())
    return out
