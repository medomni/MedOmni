"""The family registry: Core's family files (`core/families/<id>.yaml`), checked against their contract.

    from medomni.core import families
    families.get("spo2-series-10hz-pct").protocol.rate_hz

A missing folder, a file that fails its contract, a file whose `id` is not its name, or a missing family is an error;
the registry is never silently empty (R1.3).
"""
from __future__ import annotations

from functools import cache
from pathlib import Path

from medomni.core import plugins

FOLDER = "core/families"
ALIASES = "aliases.yaml"


class FamilyError(LookupError):
    pass


def folder(root: Path | None = None) -> Path:
    """The families folder: `<root>/core/families`, by default in the repository holding the current folder."""
    if root is None:
        root = plugins.find_repo()
        if root is None:
            raise FamilyError("no MedOmni repository found, so no family registry (core/families/). Built-in content "
                              "is read from the repository: run inside a clone installed with `uv pip install -e .` "
                              "(Get started). A plug-in's CI checks out MedOmni the same way.")
    d = Path(root) / FOLDER
    if not d.is_dir():
        raise FamilyError(f"family registry folder missing: {d}")
    return d


@cache
def _load(d: Path) -> dict:
    from medomni.core.contracts import FamilyFile, load

    out = {}
    for p in sorted(d.glob("*.yaml")):
        if p.name == ALIASES:
            continue
        f = load(p, FamilyFile)
        if f.id != p.stem:
            raise FamilyError(f"{p}: id '{f.id}' differs from the file name")
        out[f.id] = f
    if not out:
        raise FamilyError(f"no family files in {d}")
    return out


def load_registry(root: Path | None = None) -> dict:
    """{family id: FamilyFile} for every family file."""
    return dict(_load(folder(root).resolve()))


def get(family_id: str, root: Path | None = None):
    reg = _load(folder(root).resolve())
    try:
        return reg[family_id]
    except KeyError:
        raise FamilyError(f"unknown family '{family_id}'") from None
