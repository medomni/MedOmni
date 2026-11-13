"""The data check: no patient ids, key shapes or stray data files in what MedOmni publishes (s4 part 6; step 7 runs
it before every push and in the local CI script).

It reads files as bytes and reports hits by pattern, never the matched text. A hit is resolved by a rule in
`release/datacheck-allow.yaml` (a path glob, the pattern, and why it isn't patient data); every other hit fails.

    python release/datacheck.py tree [<ref>]       # the files at <ref> (default: HEAD)
    python release/datacheck.py history <ref>      # every version of every file reachable from <ref>
    --release       only the release tree (release/public.yaml), as on the private line
    --extra <file>  more patterns, one regex per line (the private line's own, such as private paths)
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

PATTERNS = {
    # MIMIC subject, admission and stay ids: eight digits from 1, standing alone (not inside a hash or a longer number)
    "mimic-id": re.compile(rb"(?<![0-9A-Za-z.])p?1\d{7}(?![0-9A-Za-z.])"),
    "bids-subject": re.compile(rb"\bsub-[A-Z]?\d{3,}\b"),
    "key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}|\bhf_[A-Za-z0-9]{30,}|\bghp_[A-Za-z0-9]{30,}|\bAKIA[0-9A-Z]{16}\b"),
}
DATA = {".edf", ".bdf", ".dat", ".hea", ".atr", ".dcm", ".h5", ".hdf5", ".npz", ".npy", ".parquet", ".vital", ".mat",
        ".pt", ".pth", ".pkl", ".csv", ".tsv", ".jsonl", ".gz", ".zst", ".zip"}
DATA_HOMES = ("*/testdata/*", "*/fixtures/*", "docs/*")  # where data files may live (each with a PROVENANCE)
ALLOW = Path(__file__).with_name("datacheck-allow.yaml")


def patterns(extra: Path | None = None) -> dict:
    out = dict(PATTERNS)
    if extra is not None:
        for i, line in enumerate(l for l in extra.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")):
            out[f"extra-{i + 1}"] = re.compile(line.strip().encode())
    return out


def rules(path: Path = ALLOW) -> list[dict]:
    import yaml

    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("allow", []) if path.is_file() else []


def hits(path: str, data: bytes, pats: dict) -> dict[str, set]:
    """{pattern: the matched values} of a file version, and `data-file` for a data file outside its homes."""
    out = {}
    for name, rx in pats.items():
        found = {m.group(0).decode(errors="replace").lstrip("p") for m in rx.finditer(data)}
        if found:
            out[name] = found
    if Path(path).suffix.lower() in DATA and not any(fnmatch.fnmatchcase(path, h) for h in DATA_HOMES):
        out["data-file"] = {path}
    return out


def resolve(path: str, pattern: str, values: set, allow: list[dict]) -> str | None:
    """The reason a hit is allowed, or None. A rule with `values` allows only those values (each must be one); a rule
    without allows the pattern anywhere in the files its path glob names."""
    mine = [r for r in allow if r["pattern"] == pattern and fnmatch.fnmatchcase(path, r["path"])]
    for r in mine:
        if "values" not in r:
            return r["reason"]
    left = set(values)
    reasons = []
    for r in mine:
        ok = left & {str(v) for v in r["values"]}
        if ok:
            left -= ok; reasons.append(r["reason"])
    return "; ".join(reasons) if reasons and not left else None


def _git(repo, *args, inp=None) -> bytes:
    return subprocess.run(["git", *args], cwd=repo, input=inp, capture_output=True, check=True).stdout


def released(path: str, include: list[str] | None) -> bool:
    return include is None or path.split("/", 1)[0] in include


def include_list(repo) -> list[str]:
    """The top-level entries `release/public.yaml` publishes."""
    import yaml

    return list(yaml.safe_load((Path(repo) / "release/public.yaml").read_text(encoding="utf-8"))["include"])


def versions(repo, ref: str, history: bool, include: list[str] | None = None) -> list[tuple[str, str]]:
    """(path, blob) of every file at <ref>, or of every version reachable from <ref>, each blob once; only the release
    tree's when `include` is given."""
    if not history:
        rows = _git(repo, "ls-tree", "-r", ref).decode().splitlines()
        return [(r.split("\t", 1)[1], r.split()[2]) for r in rows
                if r.split()[1] == "blob" and released(r.split("\t", 1)[1], include)]
    seen, out = set(), []
    for sha in _git(repo, "rev-list", ref).decode().split():
        for r in _git(repo, "ls-tree", "-r", sha).decode().splitlines():
            meta, path = r.split("\t", 1)
            blob = meta.split()[2]
            if meta.split()[1] == "blob" and (path, blob) not in seen and released(path, include):
                seen.add((path, blob)); out.append((path, blob))
    return out


def check(repo, ref: str = "HEAD", history: bool = False, extra: Path | None = None, allow: list[dict] | None = None,
          include: list[str] | None = None):
    """{"versions": n, "hits": [(path, pattern, reason or None)]} for the files at <ref>, or for all of its history."""
    pats, allow = patterns(extra), rules() if allow is None else allow
    vs = versions(repo, ref, history, include)
    blobs = {}
    if vs:
        out = _git(repo, "cat-file", "--batch", inp=("\n".join(sorted({b for _, b in vs})) + "\n").encode())
        i = 0
        while i < len(out):
            nl = out.index(b"\n", i)
            sha, _, size = out[i:nl].split()
            n = int(size)
            blobs[sha.decode()] = out[nl + 1: nl + 1 + n]
            i = nl + 2 + n
    found = []
    for path, blob in vs:
        for p, values in hits(path, blobs[blob], pats).items():
            found.append((path, p, resolve(path, p, values, allow)))
    return {"versions": len(vs), "hits": found}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="datacheck", description=__doc__.split("\n\n")[0])
    ap.add_argument("what", choices=("tree", "history"))
    ap.add_argument("ref", nargs="?", default="HEAD")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--extra", type=Path)
    ap.add_argument("--release", action="store_true", help="only the release tree (release/public.yaml)")
    a = ap.parse_args(argv)
    r = check(a.repo, a.ref, a.what == "history", a.extra, include=include_list(a.repo) if a.release else None)
    bad = [(p, k) for p, k, why in r["hits"] if why is None]
    print(f"data check: {r['versions']} file version(s), {len(r['hits'])} hit(s), {len(bad)} unresolved")
    for (k, top), n in sorted(Counter((k, p.split("/")[0]) for p, k in bad).items()):
        print(f"  {k} in {top}/: {n}")
    for p, k in bad[:50]:
        print(f"  {k}: {p}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
