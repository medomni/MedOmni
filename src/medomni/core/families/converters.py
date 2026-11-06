"""Family converters: code that turns a source format into a family's form, such as h5 into EDF.

A converter is a Python piece in the `medomni.converters` entry-point group; its entry-point name is its `name`.
`version` goes into cache keys (part 7), so a changed converter never reuses an old conversion.
Two converters with one name are both refused (R-65).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from medomni.core import plugins


@dataclass(frozen=True)
class ConvertFacts:
    """What one conversion wrote."""

    path: Path  # the converted file
    sha256: str
    notes: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class FamilyConverter(Protocol):
    name: str  # e.g. "h5-to-edf"
    version: str
    source_format: str  # e.g. "h5"
    families: frozenset[str]

    def convert(self, src: Path, family, out: Path) -> ConvertFacts: ...


@dataclass(frozen=True)
class Converters:
    found: dict[str, FamilyConverter]
    errors: tuple[str, ...]


def load() -> Converters:
    """Every installed converter, imported and checked; clashes and broken pieces are listed in `errors`."""
    r = plugins.resolve(plugins.CONVERTERS)
    found, errors = {}, [msg for _, msg in r.errors]
    for name, piece in sorted(r.pieces.items()):
        try:
            obj = piece.load()
        except plugins.PluginError as e:
            errors.append(str(e))
            continue
        if not isinstance(obj, FamilyConverter):
            errors.append(f"{piece.full_name}: not a family converter (needs name, version, source_format, "
                          "families, convert)")
        elif obj.name != name:
            errors.append(f"{piece.full_name}: registered as '{name}' but names itself '{obj.name}'")
        else:
            found[name] = obj
    return Converters(found, tuple(errors))


def for_family(family_id: str, source_format: str, converters: Converters | None = None) -> FamilyConverter:
    c = converters or load()
    matches = [x for x in c.found.values() if x.source_format == source_format and family_id in x.families]
    if len(matches) != 1:
        names = ", ".join(sorted(x.name for x in matches)) or "none"
        raise LookupError(f"{len(matches)} converters from {source_format} to {family_id} ({names}); need one")
    return matches[0]
