"""The encoder deployment record, read-only (fix roadmap encoder-images.md §2.2a, schema
medomni.deployed/1, revised 2026-09-24: no registry — the pin is the LOCAL image content id).
Pure python: used by the perception service at run time, and by tests.

The service serves an encoder only if the record says it may: an entry exists, its image_id is
recorded, its L2 stage PASSED and its L3 stage did not fail, both at the entry's own build_key. An unverified
L3 (no real samples given, or an access-controlled family) is accepted: the test data (L2) stands in
(Bosong, 2026-11-11; every family since R-161). Whether the entry is
STALE against the current source is not checked here — that needs the repo and is the launch
gate's job.
"""
from __future__ import annotations

from pathlib import Path

import yaml

SCHEMA = "medomni.deployed/1"
UNVERIFIED = "UNVERIFIED"  # an L3 with no real samples to run: the test data stands in
ACCESS_CONTROLLED = "UNVERIFIED-access-controlled"  # L3 for a family whose samples aren't distributed
NO_SAMPLES = "UNVERIFIED-no-samples"  # L3 when no real samples were given (`--samples`)


def load(path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    doc = yaml.safe_load(p.read_text()) or {}
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"{p}: schema {doc.get('schema')!r}, expected {SCHEMA!r}")
    return doc


def entry(rec: dict | None, encoder_id: str) -> dict | None:
    return ((rec or {}).get("encoders") or {}).get(encoder_id)


def servable(rec: dict | None, encoder_id: str) -> tuple[bool, str]:
    e = entry(rec, encoder_id)
    if e is None:
        return False, "no record entry"
    if not str(e.get("image_id") or "").startswith("sha256:"):
        return False, "record entry without an image_id pin"
    for stage in ("L2", "L3"):
        s = (e.get("stages") or {}).get(stage) or {}
        if s.get("build_key") != e.get("build_key"):
            return False, f"{stage} result is for another build_key"
        if s.get("status") != "PASS" and not (stage == "L3" and str(s.get("status") or "").startswith(UNVERIFIED)):
            return False, f"{stage} {s.get('status') or 'missing'}"
    return True, "ok"


def ref(rec: dict | None, encoder_id: str) -> str | None:
    """What the gateway runs: the recorded image content id (`sha256:…`), never the mutable :dev tag."""
    e = entry(rec, encoder_id)
    return e["image_id"] if e and str(e.get("image_id") or "").startswith("sha256:") else None
