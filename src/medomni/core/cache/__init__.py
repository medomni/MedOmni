"""The cache (Cache page; R-39, R-48): results of slow steps, kept once per key.

    <workspace>/cache/<dataset>/<step>/<key>/
        CACHE.json      the step, version, parameters, inputs with their hashes, row counts, content hash
        ...             the entry's files

- The key is sha256 over canonical JSON of the step name, step version, parameters and the inputs' hashes. Raw-file
  inputs are hashed with `sha256_file`; entry inputs by their content hash.
- An entry is never changed. Creating an existing key does nothing and says so.
- An entry is written into `<key>.tmp-<pid>/` and then renamed, so a crash leaves only a `.tmp-` folder,
  which `gc` removes. No links and no permission changes: it works on exFAT.
- The content hash is `dir_hash` of the entry without `CACHE.json`; `verify` recomputes it.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from medomni.core import hashing

META = "CACHE.json"
TMP = ".tmp-"


class CacheError(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def key(step: str, version: str, params: dict, inputs: list[tuple[str, str]]) -> str:
    """The key of an entry: inputs are (name, hash) pairs; their order does not count."""
    doc = {"step": step, "version": version, "params": params, "inputs": sorted([n, h] for n, h in inputs)}
    import hashlib

    return hashlib.sha256(canonical(doc).encode("utf-8")).hexdigest()


def file_input(path: Path, name: str) -> tuple[str, str]:
    """A raw file as an input: its name (relative to the data root) and its sha256."""
    return name, hashing.sha256_file(path)


@dataclass(frozen=True)
class Entry:
    path: Path
    meta: Any  # CacheEntry

    @property
    def name(self) -> str:
        return f"{self.meta.dataset}/{self.meta.step}/{self.meta.key}"

    def as_input(self) -> tuple[str, str]:
        return self.name, self.meta.content_hash


def _release() -> str:
    from medomni import __version__

    return __version__


class Cache:
    def __init__(self, root: Path):
        root = Path(root)
        if not root.is_absolute():
            raise CacheError(f"cache root must be absolute: {root}")
        self.root = root

    def folder(self, dataset: str, step: str, k: str) -> Path:
        return self.root / dataset / step / k

    def get(self, dataset: str, step: str, k: str) -> Entry | None:
        d = self.folder(dataset, step, k)
        return self.read(d) if (d / META).is_file() else None

    @staticmethod
    def read(d: Path) -> Entry:
        from medomni.core.contracts import CacheEntry, load

        return Entry(d, load(d / META, CacheEntry))

    def create(self, dataset: str, step: str, version: str, params: dict, inputs: list[tuple[str, str]],
               write: Callable[[Path], dict[str, int]]) -> tuple[Entry, bool]:
        """(entry, created). `write(folder)` writes the entry's files and returns its row counts."""
        from medomni.core.contracts import CacheEntry, load_data

        k = key(step, version, params, inputs)
        final = self.folder(dataset, step, k)
        if (final / META).is_file():
            return self.read(final), False
        final.parent.mkdir(parents=True, exist_ok=True)
        tmp = final.parent / f"{k}{TMP}{os.getpid()}"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir()
        try:
            rows = write(tmp) or {}
            if (tmp / META).exists():
                raise CacheError(f"step {step} wrote its own {META}")
            meta = load_data({"dataset": dataset, "step": step, "version": version, "key": k, "params": params,
                              "inputs": [{"name": n, "hash": h} for n, h in sorted(inputs)], "rows": rows,
                              "content_hash": hashing.dir_hash(tmp), "release": _release()}, CacheEntry, str(final))
            (tmp / META).write_text(json.dumps(meta.model_dump(mode="json", by_alias=True), indent=1) + "\n",
                                    encoding="utf-8")
            try:
                os.rename(tmp, final)
            except OSError:
                if not (final / META).is_file():
                    raise
                shutil.rmtree(tmp)  # another process made the same entry first
                return self.read(final), False
        except BaseException:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        return self.read(final), True

    def folders(self) -> Iterator[Path]:
        """Every entry folder and every `.tmp-` folder, sorted."""
        if not self.root.is_dir():
            return
        for d in sorted(self.root.glob("*/*/*")):
            if d.is_dir():
                yield d

    def entries(self) -> Iterator[Entry]:
        for d in self.folders():
            if TMP not in d.name:
                yield self.read(d)

    def find(self, k: str) -> Entry | None:
        for d in self.root.glob(f"*/*/{k}"):
            if (d / META).is_file():
                return self.read(d)
        return None


def verify(entry: Entry) -> list[str]:
    """Problems with one entry: an empty list when it is sound."""
    m = entry.meta
    problems = []
    if entry.path.name != m.key or entry.path.parent.name != m.step or entry.path.parent.parent.name != m.dataset:
        problems.append(f"filed under {entry.path.parent.parent.name}/{entry.path.parent.name}/{entry.path.name}, "
                        f"but {META} says {entry.name}")
    if key(m.step, m.version, m.params, [(i.name, i.hash) for i in m.inputs]) != m.key:
        problems.append(f"{META}'s step, version, parameters and inputs do not give its key")
    try:
        actual = hashing.dir_hash(entry.path, exclude=(META,))
    except hashing.HashError as e:
        problems.append(str(e))
    else:
        if actual != m.content_hash:
            problems.append(f"content hash {actual[:12]}… differs from {META}'s {m.content_hash[:12]}…: "
                            "a file was changed, added or removed")
    return problems


def size(d: Path) -> int:
    return sum(p.stat().st_size for p in d.rglob("*") if p.is_file())


# Core's own cache steps and their versions. Raising a version gives new keys; `gc` removes the old entries.
CORE_STEPS: dict[str, str] = {"events": "1"}  # loading a dataset into its event table (part 6)


def current_steps() -> dict[str, str]:
    """{step: version} for every step the installed code runs: Core's, and one `convert-<name>` per converter."""
    from medomni.core.families import converters

    steps = dict(CORE_STEPS)
    steps.update({f"convert-{c.name}": c.version for c in converters.load_all().found.values()})
    return steps


def in_use(entry: Entry, steps: dict[str, str]) -> bool:
    return steps.get(entry.meta.step) == entry.meta.version
