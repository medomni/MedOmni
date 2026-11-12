"""`medomni contracts check [<contract> ...]`: validate every contract file in the repository and installed plug-ins.

Content files are found by the patterns each project registers in `medomni.content` (R-145); Core adds only its own
family files. Plug-in folders use the same layout and are read the same way (R-69); family files come from the repository only.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from medomni.core import plugins

from . import AliasFile, ContractError, FamilyFile, load

REPO, PLUGINS, BOTH = plugins.REPO, plugins.PLUGIN_FOLDERS, plugins.BOTH

# Core's own files; every project's come from `medomni.content` (R-145)
CORE = (
    plugins.Files("family registry", "families", "core/families/*.yaml", FamilyFile, exclude=("aliases.yaml",), where=REPO),
    plugins.Files("family registry", "families", "core/families/aliases.yaml", AliasFile, where=REPO),
)


def contents() -> tuple[plugins.Files, ...]:
    return CORE + plugins.content_kinds()[1]


def aliases() -> dict[str, str]:
    """Short names accepted on the command line, as on the reference pages."""
    return {c.alias: c.contract for c in contents()}


@dataclass(frozen=True)
class Result:
    package: str
    contract: str
    path: Path
    label: str  # repository-relative path, or `<package>:<path in its folder>`
    error: str | None


def results(roots: list[tuple[str, Path]], only: set[str] | None = None):
    """Validate every contract file under the roots (repository first, then plug-in folders)."""
    for package, root in roots:
        builtin = package == plugins.BUILTIN
        for c in contents():
            if (only and c.contract not in only) or c.where == (PLUGINS if builtin else REPO):
                continue
            for p in sorted(root.glob(c.pattern)):
                if any(p.match(x) for x in c.exclude):
                    continue
                rel = p.relative_to(root).as_posix()
                label = rel if builtin else f"{package}:{rel}"
                try:
                    load(p, c.model)
                    yield Result(package, c.contract, p, label, None)
                except ContractError as e:
                    yield Result(package, c.contract, p, label, str(e))


def check(repo: Path | None, only: set[str] | None = None, out=None) -> tuple[dict[str, list[int]], int]:
    """Returns ({contract: [ok, failed]}, failures)."""
    out = out or sys.stdout
    roots, bad = plugins.roots(repo)
    counts: dict[str, list[int]] = {}
    failed = 0
    for f in bad:
        failed += 1
        print(f"FAIL  {f.error}", file=out)
    for r in results(roots, only):
        c = counts.setdefault(r.contract, [0, 0])
        if r.error is None:
            c[0] += 1
            print(f"ok    {r.label}", file=out)
        else:
            c[1] += 1
            failed += 1
            print(f"FAIL  {r.error}", file=out)
    return counts, failed


HELP = ("usage: medomni contracts check [<contract> ...]\n\nValidates every contract file in the repository (when run "
        "inside one) and in the installed plug-in folders.\nContracts: ")


def main(argv: list[str]) -> int:
    if (argv[:1] or [""])[0] in ("-h", "--help") or (argv[:1] == ["check"] and {"-h", "--help"} & set(argv[1:])):
        print(HELP + ", ".join(sorted(aliases())))
        return 0
    if not argv or argv[0] != "check":
        print("usage: medomni contracts check [<contract> ...]", file=sys.stderr)
        return 2
    names, known = argv[1:], aliases()
    unknown = [n for n in names if n not in known and n not in known.values()]
    if unknown:
        print(f"medomni contracts check: unknown contract {', '.join(unknown)}", file=sys.stderr)
        return 2
    only = {known.get(n, n) for n in names} or None
    counts, failed = check(plugins.find_repo(), only)
    passed = sum(ok for ok, _ in counts.values())
    total = sum(ok + bad for ok, bad in counts.values())
    summary = ", ".join(f"{k} {ok}/{ok + bad}" for k, (ok, bad) in sorted(counts.items())) or "no files"
    print(f"{passed}/{total} files pass: {summary}")
    return 1 if failed else 0
