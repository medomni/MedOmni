"""Core's hash functions (R1.4, U2.3).

- `sha256_file`: the SHA-256 of a whole file, read in chunks.
- `quick_sha`: a cheap identity for large recordings (size, first MiB, last MiB above 2 MiB), 16 hex characters.
  It gives the values v0.2's manifest builder stored.
- `dir_hash`: a folder's SHA-256, every file in path order, each entry length-prefixed.
- `config_hash`: `cfg1:` + SHA-256 over a task's config files and the dataset and MedOmni release names (R-111,
  R-112). It is published, so its recipe never changes under the `cfg1:` prefix.

Nothing is hashed over built data to align results (R-111). v0.2's exact hash recipes live only in the reproduction
test (R-118).
"""
from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path

CHUNK = 4 << 20
MIB = 1 << 20
CONFIG_PREFIX = "cfg1:"


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


def config_hash(files: Mapping[str, str | os.PathLike | bytes], *, dataset_release: str, medomni_release: str) -> str:
    """`cfg1:` + sha256 over a task's config files and its releases.

    `files` maps each config file's name (repository-relative, POSIX) to its path or bytes. Names are taken in sorted
    order; each adds `<name>\\0<length>\\0<bytes>`, as in `dir_hash`. Then `dataset\\0<release>\\0` and
    `medomni\\0<release>\\0`. Data files are never listed (R-111): the hash says the config matched, not the data.
    """
    h = hashlib.sha256()
    for name in sorted(files):
        if "\0" in name:
            raise HashError(f"{name!r}: a config file name holds a NUL")
        src = files[name]
        data = src if isinstance(src, bytes) else Path(src).read_bytes()
        h.update(name.encode("utf-8") + b"\0" + str(len(data)).encode() + b"\0" + data)
    for label, release in (("dataset", dataset_release), ("medomni", medomni_release)):
        if not release or "\0" in release:
            raise HashError(f"{label} release {release!r}: empty or holds a NUL")
        h.update(label.encode() + b"\0" + release.encode("utf-8") + b"\0")
    return CONFIG_PREFIX + h.hexdigest()
