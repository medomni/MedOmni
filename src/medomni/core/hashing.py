"""Core's hash functions (R1.4, U2.3).

- `sha256_file`: the SHA-256 of a whole file, read in chunks.
- `quick_sha`: a cheap identity for large recordings (size, first MiB, last MiB above 2 MiB), 16 hex characters.
  It gives the values v0.2's manifest builder stored.
- `dir_hash`: a folder's SHA-256, every file in path order, each entry length-prefixed.
- `fingerprint`: `fp1:` + `dir_hash` of a built `<template>@<cohort>`, without its `FINGERPRINT` file
  (Tasks reference, "Fingerprint").

v0.2 code whose stored outputs depend on its exact recipe (the bridge's own `quick_sha`, `BRIDGE_VERSION`,
`emit.sha256_dir` and 13 others) keeps it, and moves with its area in Stage 3.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

CHUNK = 4 << 20
MIB = 1 << 20
FP_PREFIX = "fp1:"
FINGERPRINT_FILE = "FINGERPRINT"


class HashError(ValueError):
    """A folder cannot be hashed: it holds a link or something that is not a file."""


def _update_file(h, path: Path, chunk: int = CHUNK) -> None:
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)


def sha256_file(path: str | os.PathLike, chunk: int = CHUNK) -> str:
    h = hashlib.sha256()
    _update_file(h, Path(path), chunk)
    return h.hexdigest()


def quick_sha(path: str | os.PathLike) -> str:
    """sha256 over the size, the first MiB, and the last MiB when the file is larger than 2 MiB; first 16 hex."""
    p = Path(path)
    h = hashlib.sha256()
    size = p.stat().st_size
    h.update(str(size).encode())
    with open(p, "rb") as f:
        h.update(f.read(MIB))
        if size > 2 * MIB:
            f.seek(-MIB, os.SEEK_END)
            h.update(f.read(MIB))
    return h.hexdigest()[:16]


def files(root: str | os.PathLike, exclude: tuple[str, ...] = ()) -> list[str]:
    """Every file under `root` as a relative POSIX path, sorted. Links are refused, never followed."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise HashError(f"{root}: not a folder")
    out = []
    for base, dirs, names in os.walk(root):
        for n in (*dirs, *names):
            p = Path(base) / n
            if p.is_symlink():
                raise HashError(f"{p}: a link; a hashed folder holds its files, not links to them")
            if n in names and not p.is_file():
                raise HashError(f"{p}: not a regular file")
        out += [(Path(base) / n).relative_to(root).as_posix() for n in names]
    return sorted(r for r in out if r not in exclude)


def dir_hash(root: str | os.PathLike, exclude: tuple[str, ...] = ()) -> str:
    """sha256 over every file in path order; each adds `<path>\\0<length>\\0<bytes>`.

    The path ends at the NUL, which no path holds, and the length bounds the bytes, so no two folders share a stream.
    File times and permissions do not count.
    """
    root = Path(root)
    h = hashlib.sha256()
    for rel in files(root, exclude):
        p = root / rel
        h.update(rel.encode("utf-8") + b"\0" + str(p.stat().st_size).encode() + b"\0")
        _update_file(h, p)
    return h.hexdigest()


def fingerprint(folder: str | os.PathLike) -> str:
    """The `fp1:` fingerprint of a built `<template>@<cohort>` folder."""
    return FP_PREFIX + dir_hash(folder, exclude=(FINGERPRINT_FILE,))
