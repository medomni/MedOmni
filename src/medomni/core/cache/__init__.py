"""The cache (Cache page; research/cache-design.md, R-155): results of slow steps, kept so a later build can skip them.

- It only saves time. Deleting it loses nothing but time; nothing checks, compares or publishes what it holds (R-111).
- A step is a function of its arguments: dataset, step name, step version, parameters and inputs, where each input
  is a (name, identity) pair, such as a raw file and its quick fingerprint (R-130). The key is built from those
  arguments alone (`key`).
- A backend has one call, `run(dataset, step, version, params, inputs, make) -> (Result, created)`. `make(folder)`
  writes the step's files into an empty folder and may return row counts; `run` returns a folder holding those
  files, made now or kept from before. Callers read only that folder.
- `workspace.yaml`'s `cache` names the backend: a path (the `folder` backend there), or
  `{backend: <name>, path: …, options: {…}}`. Core ships `folder` (the default) and `none`; a plug-in package adds
  one in the `medomni.caches` entry-point group, with no change to Core.
- Optional backend features: `status()` and `gc(dry_run)`, for `medomni cache status|gc`; `has(dataset, step)`,
  for the audit; `close()`.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from medomni.core import hashing
from medomni.core.plugins import CACHES as GROUP


class CacheError(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def key(step: str, version: str, params: dict, inputs: list[tuple[str, str]]) -> str:
    """The key of a step's result: inputs are (name, identity) pairs; their order does not count."""
    doc = {"step": step, "version": version, "params": params, "inputs": sorted([n, h] for n, h in inputs)}
    return hashlib.sha256(canonical(doc).encode("utf-8")).hexdigest()


def file_input(path: Path, name: str) -> tuple[str, str]:
    """A raw file as an input: its name (relative to the data root) and its sha256."""
    return name, hashing.sha256_file(path)


@dataclass(frozen=True)
class Result:
    """A step's result: the folder holding its files, and the arguments it was made from."""

    path: Path
    dataset: str
    step: str
    version: str
    key: str
    params: dict = field(default_factory=dict)
    inputs: tuple[str, ...] = ()  # the input names
    rows: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"{self.dataset}/{self.step}/{self.key}"


Make = Callable[[Path], "dict[str, int] | None"]


class Backend(Protocol):
    name: str
    spec: dict  # what `open_cache` needs to open the same cache again, in another process

    def run(self, dataset: str, step: str, version: str, params: dict, inputs: list[tuple[str, str]],
            make: Make) -> tuple[Result, bool]: ...


def check_rows(rows) -> dict[str, int]:
    rows = rows or {}
    if not isinstance(rows, dict) or not all(isinstance(k, str) and isinstance(v, int) for k, v in rows.items()):
        raise CacheError(f"a step returns row counts as {{name: int}}, not {rows!r}")
    return rows


def refuse_links(folder: Path) -> None:
    """A result holds real files only: no links, so it works on exFAT and a copy is a copy."""
    for p in folder.rglob("*"):
        if p.is_symlink():
            raise CacheError(f"a step wrote a link, {p.relative_to(folder)}; write real files")


# ---------------------------------------------------------------- choosing a backend

DEFAULT = "folder"


def _builtin(name: str):
    if name == "folder":
        from .folder import FolderCache
        return FolderCache
    if name == "none":
        from .none import NoCache
        return NoCache
    return None


def spec_of(setting) -> dict:
    """`workspace.yaml`'s `cache` value as {backend, path, options}: a bare path is the `folder` backend there."""
    if setting is None:
        raise CacheError("the workspace config has no `cache`")
    if isinstance(setting, (str, Path)):
        return {"backend": DEFAULT, "path": str(setting), "options": {}}
    if hasattr(setting, "model_dump"):
        setting = setting.model_dump()
    return {"backend": setting.get("backend") or DEFAULT, "path": setting.get("path"),
            "options": dict(setting.get("options") or {})}


def open_cache(setting) -> Backend:
    """The backend `setting` names: Core's `folder` or `none`, or one from a plug-in package (`medomni.caches`)."""
    spec = spec_of(setting)
    name = spec["backend"]
    cls = _builtin(name)
    if cls is None:
        from medomni.core import plugins

        found = plugins.resolve(GROUP)
        piece = found.pieces.get(name)
        if piece is None:
            known = sorted({"folder", "none", *found.pieces})
            raise CacheError(f"no cache backend '{name}'; known: {', '.join(known)}")
        cls = piece.load()
    return cls(path=spec["path"], **spec["options"])


def of(ws) -> Backend:
    """The workspace's cache backend."""
    return open_cache(ws.cache)


# ---------------------------------------------------------------- steps the installed code runs

# Core's own cache steps and their versions. Raising a version gives new keys; `gc` removes the old results.
CORE_STEPS: dict[str, str] = {"events": "1"}  # loading a dataset into its event table (part 6)


def current_steps() -> dict[str, str]:
    """{step: version} for every step the installed code runs: Core's, and one `convert-<name>` per converter."""
    from medomni.core.families import converters

    steps = dict(CORE_STEPS)
    steps.update({f"convert-{c.name}": c.version for c in converters.load_all().found.values()})
    return steps


def size(d: Path) -> int:
    return sum(p.stat().st_size for p in d.rglob("*") if p.is_file())
