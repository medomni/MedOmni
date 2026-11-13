"""The push guard (s4 part 7, R-164, R-169): run by `release/hooks/pre-push` before every push.

To the public remote (named `public`, or whose URL is the one `release/public.yaml` names) a push is accepted only
when it is the export's output: `refs/export/main` to `main`, or `refs/export/tags/<v>` to `<v>`, never a deletion.
Every commit it brings must hold only the release tree's top-level entries, and every file version it brings must
pass the data check, the private line's own patterns included.

To any other remote, the file versions a push brings must pass the data check's patient-data patterns (ids, key
shapes): no branch holds patient data (R-164).

    git config core.hooksPath release/hooks      # once per clone of the private repository
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ZERO = "0" * 40
EXPORT_MAIN = "refs/export/main"
EXPORT_TAGS = "refs/export/tags/"
PRIVATE_CONFIG = Path("internal_docs/release/export.yaml")


def _datacheck():
    spec = importlib.util.spec_from_file_location("datacheck", HERE / "datacheck.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git(repo, *a) -> str:
    return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, check=True).stdout


def _public_yaml(repo) -> dict:
    import yaml

    return yaml.safe_load((Path(repo) / "release/public.yaml").read_text(encoding="utf-8")) or {}


def is_public(repo, name: str, url: str) -> bool:
    want = _public_yaml(repo).get("remote", "")
    norm = lambda u: re.sub(r"(\.git)?/?$", "", re.sub(r"^(https?://|ssh://)?(git@)?", "", u).replace(":", "/"))  # noqa: E731
    return name == "public" or bool(want) and norm(url) == norm(want)


def new_commits(repo, local_sha: str, remote_sha: str, remote: str) -> list[str]:
    """The commits a push brings: those the remote's old value, or (for a new ref) the remote's known refs, lack."""
    known = remote_sha != ZERO and subprocess.run(["git", "cat-file", "-e", f"{remote_sha}^{{commit}}"], cwd=repo).returncode == 0
    args = [local_sha, "--not", remote_sha] if known else [local_sha, "--not", f"--remotes={remote}"]
    return git(repo, "rev-list", *args).split()


def problems(repo, name: str, url: str, updates: list[tuple[str, str, str, str]]) -> list[str]:
    dc = _datacheck()
    public = is_public(repo, name, url)
    out = []
    pats = dc.patterns()
    if public:
        cfg = Path(repo) / PRIVATE_CONFIG
        if cfg.is_file():
            import yaml

            for i, p in enumerate((yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("private_patterns", [])):
                pats[f"private-{i + 1}"] = re.compile(p.encode())
    include = dc.include_list(repo)
    for local_ref, local_sha, remote_ref, remote_sha in updates:
        if public:
            if local_sha == ZERO:
                out.append(f"{remote_ref}: the public repository's refs are never deleted by a push")
                continue
            tag = local_ref.startswith(EXPORT_TAGS) and remote_ref == "refs/tags/" + local_ref[len(EXPORT_TAGS):]
            if not ((local_ref == EXPORT_MAIN and remote_ref == "refs/heads/main") or tag):
                out.append(f"{local_ref} -> {remote_ref}: only the export goes public "
                           f"({EXPORT_MAIN} -> main, {EXPORT_TAGS}<v> -> <v>); run release/export.py export")
                continue
        if local_sha == ZERO:
            continue
        target = git(repo, "rev-parse", f"{local_sha}^{{commit}}").strip()
        commits = new_commits(repo, target, remote_sha, name)
        if public:
            for c in commits:
                extra = sorted({e.split("/")[0] for e in git(repo, "ls-tree", "--name-only", c).split()} - set(include))
                if extra:
                    out.append(f"{local_ref}: commit {c[:12]} holds what the release tree doesn't list: {', '.join(extra)}")
        kept = pats if public else {k: v for k, v in pats.items() if k in dc.PATTERNS}
        r = dc.check(repo, commits=commits, pats=kept, include=None)
        bad = sorted({(p, k) for p, k, why in r["hits"] if why is None and (public or k != "data-file")})
        out += [f"{local_ref}: {k} in {p}" for p, k in bad]
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    name, url = argv[0], argv[1] if len(argv) > 1 else ""
    repo = git(".", "rev-parse", "--show-toplevel").strip()
    updates = [tuple(line.split()) for line in sys.stdin.read().splitlines() if line.strip()]
    found = problems(repo, name, url, updates)
    if found:
        print(f"push to {name} refused by the guard (release/guard.py):", file=sys.stderr)
        for p in found[:40]:
            print(f"  {p}", file=sys.stderr)
        if len(found) > 40:
            print(f"  … {len(found) - 40} more", file=sys.stderr)
        print("Fix the cause; don't bypass the hook.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
