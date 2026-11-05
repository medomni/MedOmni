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
    "cache": "Build, list, verify and clean the cache.",
    "bench": "Build tasks, run agents and score them.",
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


def _check_piece(group: str, piece: plugins.Piece, obj) -> None:
    """Check a plug-in piece against its contract, for kinds whose piece is one contract file."""
    if piece.builtin or group not in (plugins.AGENTS, plugins.ENCODERS):
        return
    from pathlib import Path

    from medomni.core.contracts import load, load_data
    from medomni.core.contracts.check import PLUGIN_KINDS

    model = PLUGIN_KINDS[group]
    load(Path(obj), model) if isinstance(obj, (str, Path)) else load_data(obj, model, piece.full_name)


def cmd_plugins(argv: list[str]) -> int:
    """Import every installed piece and list it, with any errors."""
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
                obj = piece.load()
                _check_piece(group, piece, obj)
                rows.append(f"  {piece.full_name:<40} ok")
            except Exception as e:  # import errors and contract errors are listed, never raised
                failed += 1
                rows.append(f"  {piece.full_name:<40} error: {e}")
        for piece, msg in r.errors:
            failed += 1
            rows.append(f"  {piece.full_name:<40} error: {msg}")
        if rows:
            print(group)
            print("\n".join(rows))
    return 1 if failed else 0


def cmd_contracts(argv: list[str]) -> int:
    from medomni.core.contracts.check import main as check_main  # pydantic is imported only here

    return check_main(argv)


def _not_built(name: str) -> int:
    print(f"medomni {name}: not built yet", file=sys.stderr)
    return 1


CORE = {
    "plugins": cmd_plugins,
    "contracts": cmd_contracts,
    "cache": lambda argv: _not_built("cache"),
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
