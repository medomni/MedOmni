"""The `medomni` command.

`medomni --help` reads command names from entry-point metadata and imports no project. A project's code is imported
only when its command runs.
"""
from __future__ import annotations

import sys

from medomni.core import plugins

USAGE = "usage: medomni [--help] [--version] <command> [<args>]"

# One-line help for built-in commands, so that --help needs no import.
HELP = {
    "plugins": "List the installed plug-in packages and what each adds.",
    "contracts": "Validate the contract files.",
    "cache": "Build, list and clean the cache.",
    "bench": "Run agents on built task sets and score them.",
    "perception": "Pull and run encoders; the gateway.",
    "studio": "Make tasks: survey, propose, review, preview, report.",
}


def _version() -> str:
    from medomni import __version__

    return __version__


def _help(commands: plugins.Resolved) -> str:
    lines = [USAGE, "", f"MedOmni {_version()}", "", "Core:"]
    lines += [f"  {n:<12} {HELP[n]}" for n in plugins.CORE_COMMANDS]
    builtin = [n for n, p in commands.pieces.items() if p.builtin]
    extra = [n for n, p in commands.pieces.items() if not p.builtin]
    if builtin:
        lines += ["", "Projects:"]
        lines += [f"  {n:<12} {HELP.get(n, '')}".rstrip() for n in builtin]
    if extra:
        lines += ["", "Plug-in commands:"]
        lines += [f"  {n:<12} from {commands.pieces[n].package}" for n in sorted(extra)]
    lines += ["", "Run `medomni <command> --help` for a command's options."]
    return "\n".join(lines)


def _report(commands: plugins.Resolved) -> None:
    for w in commands.warnings:
        plugins.warn(w)
    for piece, msg in commands.errors:
        print(f"error: {msg}", file=sys.stderr)


def _list_content(failed: int) -> int:
    """List each plug-in folder's pieces by kind, checked against their contracts. Returns the updated failure count."""
    from medomni.core.contracts.check import results  # pydantic is imported only here

    roots, bad = plugins.roots(plugins.find_repo())
    kinds = plugins.content(roots)
    errors: dict[plugins.Content, list[str]] = {}
    for piece, msg in (e for r in kinds.values() for e in r.errors):
        errors.setdefault(piece, []).append(msg)
    pieces = sorted({*(p for r in kinds.values() for p in r.pieces.values()), *errors},
                    key=lambda p: (p.package, p.kind, p.name))
    by_path = {p.path: p for p in pieces}
    for r in results([(pkg, root) for pkg, root in roots if pkg != plugins.BUILTIN]):  # the repository: contracts check
        if r.error is None:
            continue
        piece = next((by_path[d] for d in (r.path, *r.path.parents) if d in by_path), None)
        if piece is not None:  # the most specific piece holding the file
            errors.setdefault(piece, []).append(r.error)
        else:  # a file in a plug-in folder that belongs to no piece
            failed += 1
            print(f"  error: {r.error}")
    folders = {(f.package, f.path) for f in plugins.folders() if f.path is not None}
    if folders or bad:
        print(plugins.PLUGINS)
    for package, path in sorted(folders):
        print(f"  {package}  {path}")
        for p in (p for p in pieces if p.package == package):
            msgs = errors.get(p, [])
            failed += bool(msgs)
            print(f"    {p.kind[:-1]:<9} {p.full_name:<40} " + ("ok" if not msgs else "error: " + "; ".join(msgs)))
    for f in bad:
        failed += 1
        print(f"  {f.package}  error: {f.error}")
    # a built-in piece that clashes with a plug-in piece is not loaded either
    for p in (p for p in errors if p.builtin):
        failed += 1
        print(f"  {p.full_name:<40} error: " + "; ".join(errors[p]))
    return failed


def cmd_plugins(argv: list[str]) -> int:
    """List every installed piece, with any errors: Python pieces are imported, content is checked."""
    if argv and argv[0] in ("-h", "--help"):
        print("usage: medomni plugins\n\n" + HELP["plugins"])
        return 0
    failed = 0
    for group in plugins.GROUPS:
        r = plugins.resolve(group)
        for w in r.warnings:
            plugins.warn(w)
        rows = []
        for name, piece in sorted(r.pieces.items()):
            try:
                piece.load()
                rows.append(f"  {piece.full_name:<40} ok")
            except plugins.PluginError as e:  # import errors are listed, never raised
                failed += 1
                rows.append(f"  {piece.full_name:<40} error: {e}")
        for piece, msg in r.errors:
            failed += 1
            rows.append(f"  {piece.full_name:<40} error: {msg}")
        if rows:
            print(group)
            print("\n".join(rows))
    failed = _list_content(failed)
    return 1 if failed else 0


def cmd_contracts(argv: list[str]) -> int:
    from medomni.core.contracts.check import main as check_main  # pydantic is imported only here

    return check_main(argv)


def cmd_cache(argv: list[str]) -> int:
    from medomni.core.cache.commands import main as cache_main

    return cache_main(argv)


CORE = {
    "plugins": cmd_plugins,
    "contracts": cmd_contracts,
    "cache": cmd_cache,
}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        commands = plugins.resolve(plugins.COMMANDS)
        _report(commands)
        print(_help(commands))
        return 0
    if argv[0] == "--version":
        print(f"medomni {_version()}")
        return 0
    name, rest = argv[0], argv[1:]
    if name in CORE:
        return CORE[name](rest)
    commands = plugins.resolve(plugins.COMMANDS)
    _report(commands)
    piece = commands.pieces.get(name)
    if piece is None:
        print(f"medomni: unknown command '{name}'\n{USAGE}", file=sys.stderr)
        return 2
    try:
        run = piece.load()
    except plugins.PluginError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return int(run(rest) or 0)


if __name__ == "__main__":
    sys.exit(main())
