"""`medomni perception check --record`: write a passing encoder into the deployment record, `perception/deployed.yaml`
(schema medomni.deployed/1). The perception service starts only the image this record pins, by content id, and serves
only an entry whose L2 and L3 passed at its own build_key (`sidecar/record.py` reads it; the service image bakes a copy).

The stages are the steps of `check`: L0 the card, L1 the image build, L2 the test data, L3 the family's real samples
(`UNVERIFIED-no-supply` when the family publishes none, which the service refuses to serve). An entry is written only
for an image built from committed source, so its `source_rev` names a commit. Other entries are left as they are,
except an entry whose encoder has no folder in any content root (the repository or a plug-in folder): it is dropped,
so the record lists only encoders that exist (s4 part 2).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

from . import LABEL_NS, RegistryError, encoder_id, repo_root, tag
from .build import SHARED, build_key, git_rev, image_labels

RECORD = Path("perception/deployed.yaml")
SCHEMA = "medomni.deployed/1"
HEADER = ("# Deployed encoder images: written by `medomni perception check --record`, do not edit.\n"
          "# Facts only. The perception service starts the pinned image_id and serves an entry whose L2 and L3\n"
          "# passed at its build_key. Schema medomni.deployed/1.\n")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def known_encoders(repo) -> set[str]:
    """The encoder ids with a folder in a content root: the repository's and every plug-in folder's."""
    from medomni.core import plugins
    from medomni.perception.content import CONTENT

    marker = next(k.marker for k in CONTENT if getattr(k, "name", None) == "encoders")
    roots, _ = plugins.roots(Path(repo))
    return {f"{card.parent.parent.name}__{card.parent.name}" for _, root in roots for card in root.glob(marker)}


def write(edir, l2_detail: str, l3_status: str, l3_detail: str | None = None, repo=None, at: str | None = None) -> dict:
    """Record the encoder's current `:dev` image as passed; returns the entry. Raises RegistryError when the image
    wasn't built from the current, committed source."""
    edir = Path(edir).resolve()
    repo = Path(repo or repo_root(edir)).resolve()
    eid = encoder_id(edir)
    key = build_key(edir, repo)
    rev = git_rev([repo / p for p in SHARED] + [edir], repo)
    if rev == "dev-dirty":
        raise RegistryError(f"{eid}: not recorded: the encoder folder or the shared runtime has uncommitted changes")
    image = tag(eid)
    labels, image_id = image_labels(image)
    if not image_id or (labels or {}).get(f"{LABEL_NS}.build_key") != key:
        raise RegistryError(f"{eid}: not recorded: {image} was not built from the current source")
    at = at or _now()

    def stage(status, detail=None):
        return {"status": status, "at": at, "build_key": key, **({"detail": detail} if detail else {})}

    entry = {"build_key": key, "source_rev": rev, "image": image, "image_id": image_id, "built_at": at,
             "stages": {"L0": stage("PASS"), "L1": stage("PASS"), "L2": stage("PASS", l2_detail),
                        "L3": stage(l3_status, l3_detail)}}
    path = repo / RECORD
    doc = (yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None) or {"schema": SCHEMA, "encoders": {}}
    if doc.get("schema") != SCHEMA:
        raise RegistryError(f"{path}: schema {doc.get('schema')!r}, expected {SCHEMA!r}")
    known = known_encoders(repo)
    encoders = {k: v for k, v in (doc.get("encoders") or {}).items() if k in known}
    encoders[eid] = entry
    doc = {"schema": SCHEMA, "encoders": dict(sorted(encoders.items()))}
    path.write_text(HEADER + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    return entry
