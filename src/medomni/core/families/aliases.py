"""One alias resolver (R1.3): what supply labels, rates, prefixes and colour modes each family accepts.

`resolve(family_id)` expands the family's `accepts` list from `core/families/aliases.yaml` into flat maps. A missing
alias file is an error, never an empty result; a family with no entry accepts nothing beyond its own protocol.
It gives the same result as v0.2's generated alias file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from . import ALIASES, FamilyError, _load, folder


@dataclass(frozen=True)
class ResolvedAliases:
    labels: dict[str, str] = field(default_factory=dict)  # supply label -> a channel or role the protocol declares
    components: dict[str, str] = field(default_factory=dict)  # supply part -> a part of a declared montage label
    rates: tuple[float, ...] = ()  # rates accepted besides the protocol's own
    prefixes: tuple[str, ...] = ()  # literal label prefixes to strip, lowercased
    colors: tuple[str, ...] = ()  # DICOM colour modes accepted, uppercased


def normalize_label(value: str) -> str:
    return re.sub(r"\s+", "-", value.strip().casefold())


def _merge(dest: dict[str, str], incoming: dict[str, str], fid: str) -> None:
    for raw_source, raw_target in incoming.items():
        source, target = normalize_label(raw_source), normalize_label(raw_target)
        if not source or not target:
            raise FamilyError(f"{fid}: alias labels must not be empty")
        if dest.get(source, target) != target:
            raise FamilyError(f"{fid}: alias '{source}' targets both '{dest[source]}' and '{target}'")
        dest[source] = target


@cache
def _alias_file(d: Path):
    from medomni.core.contracts import AliasFile, load

    p = d / ALIASES
    if not p.is_file():
        raise FileNotFoundError(f"alias file missing: {p}")
    return load(p, AliasFile)


def _resolve(fid: str, d: Path) -> ResolvedAliases:
    registry = _load(d)
    if fid not in registry:
        raise FamilyError(f"unknown family '{fid}'")
    source = _alias_file(d)
    if unknown := sorted(set(source.families) - set(registry)):
        raise FamilyError(f"{d / ALIASES}: aliases for unknown families {unknown}")
    entry = source.families.get(fid)
    if entry is None:
        return ResolvedAliases()
    protocol = registry[fid].protocol
    channels = {normalize_label(c) for c in protocol.channels} if isinstance(protocol.channels, tuple) else set()
    canonical = channels | {normalize_label(r) for r in (protocol.roles or ())}
    parts = {part for label in channels for part in label.split("-")}
    labels, components, rates, prefixes, colors = {}, {}, set(), set(), set()
    for accepted in entry.accepts:
        block = source.vocab[accepted] if isinstance(accepted, str) else accepted
        candidates: dict[str, str] = {}
        _merge(candidates, block.channels, fid)
        _merge(candidates, block.roles, fid)
        for alias, target in candidates.items():
            if target in canonical:
                _merge(labels, {alias: target}, fid)
            elif target in parts:
                _merge(components, {alias: target}, fid)
            else:
                raise FamilyError(f"{fid}: alias '{alias}' targets undeclared label '{target}'")
        rates.update(float(r) for r in block.rates)
        for prefix in block.prefixes:
            if not prefix:
                raise FamilyError(f"{fid}: prefixes must not be empty")
            prefixes.add(prefix.casefold())
        for color in block.colors:
            if not color.strip():
                raise FamilyError(f"{fid}: colors must not be empty")
            colors.add(color.strip().upper())
    return ResolvedAliases(labels=dict(sorted(labels.items())), components=dict(sorted(components.items())),
                           rates=tuple(sorted(rates)), prefixes=tuple(sorted(prefixes)), colors=tuple(sorted(colors)))


def resolve(family_id: str, root: Path | None = None) -> ResolvedAliases:
    return _resolve(family_id, folder(root).resolve())
