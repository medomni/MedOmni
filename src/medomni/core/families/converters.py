"""Family converters: code that turns a source format into a family's form, such as h5 into EDF.

A converter is a Python piece in the `medomni.converters` entry-point group, whose entry-point name is its `name`, or a
file a dataset package names in its `dataset.yaml` (`converters:`), exposing `CONVERTER` (R-145).
`version` goes into cache keys (part 7), so a changed converter never reuses an old conversion.
A converter must be deterministic: the same input gives the same bytes (no wall-clock header times, no random ids),
so two users build the same atoms, and a build with the cache equals one without it (R-155). Check 7 found the first
one that wasn't.
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


def _check(label: str, name: str, obj, found: dict, errors: list) -> None:
    if not isinstance(obj, FamilyConverter):
        errors.append(f"{label}: not a family converter (needs name, version, source_format, families, convert)")
    elif obj.name != name:
        errors.append(f"{label}: registered as '{name}' but names itself '{obj.name}'")
    elif name in found:
        errors.append(f"{label}: converter name '{name}' is already registered; neither is used")
        found.pop(name)
    else:
        found[name] = obj


def package_converters(package: Path) -> list[tuple[str, object]]:
    """(label, CONVERTER) of each file a dataset package names in its dataset.yaml `converters:`."""
    import yaml

    from medomni.core.loading.hooks import file_module

    doc = yaml.safe_load((Path(package) / "dataset.yaml").read_text(encoding="utf-8")) or {}
    out = []
    for rel in doc.get("converters", ()):
        mod = file_module(Path(package), rel, "converter")
        out.append((f"{Path(package).name}:{rel}", getattr(mod, "CONVERTER", None)))
    return out


def _load(packages: tuple[str, ...]) -> Converters:
    r = plugins.resolve(plugins.CONVERTERS)
    found, errors = {}, [msg for _, msg in r.errors]
    for name, piece in sorted(r.pieces.items()):
        try:
            obj = piece.load()
        except plugins.PluginError as e:
            errors.append(str(e))
            continue
        _check(piece.full_name, name, obj, found, errors)
    for package in packages:
        try:
            pairs = package_converters(Path(package))
        except Exception as e:  # noqa: BLE001 - a broken package file is reported, never raised through
            errors.append(f"{Path(package).name}: cannot load its converters: {type(e).__name__}: {e}")
            continue
        for label, obj in pairs:
            _check(label, getattr(obj, "name", "?"), obj, found, errors)
    return Converters(found, tuple(errors))


def load(package: Path | None = None) -> Converters:
    """The installed converters, plus a dataset package's own; clashes and broken pieces are listed in `errors`."""
    return _load((str(Path(package).resolve()),) if package is not None else ())


def load_all() -> Converters:
    """The installed converters and every dataset package's: what the cache's entries may come from."""
    from medomni.core.loading import dataset_packages

    return _load(tuple(sorted(str(p.resolve()) for p in dataset_packages())))


def for_family(family_id: str, source_format: str, converters: Converters | None = None) -> FamilyConverter:
    c = converters or load()
    matches = [x for x in c.found.values() if x.source_format == source_format and family_id in x.families]
    if len(matches) != 1:
        names = ", ".join(sorted(x.name for x in matches)) or "none"
        raise LookupError(f"{len(matches)} converters from {source_format} to {family_id} ({names}); need one")
    return matches[0]


def cached(cache, converter: FamilyConverter, dataset: str, raw_root: Path, rel: str, family_id: str,
           raw_hash: str | None = None):
    """The cache result holding `rel` (a raw file under `raw_root`) converted into `family_id`: `(entry, created)`.

    The step is `convert-<name>` at the converter's version; the params are the converter's `params(family_id)`
    when it has one (h5-to-edf hashes only what the conversion reads, R-86), else just the family; the input is the
    raw file by its sha256 (pass `raw_hash`, usually `hashing.quick_id`, for a large file several families share). The entry holds `<family>.edf`.
    """
    from medomni.core import hashing

    src = Path(raw_root) / rel
    params = converter.params(family_id) if hasattr(converter, "params") else {"family": family_id}
    digest = raw_hash or hashing.sha256_file(src)

    def write(folder: Path) -> dict[str, int]:
        converter.convert(src, family_id, folder / f"{family_id}.edf")
        return {"files": 1}

    return cache.run(dataset, f"convert-{converter.name}", converter.version, params, [(rel, digest)], write)
