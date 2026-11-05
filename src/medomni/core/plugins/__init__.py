"""Entry-point loading for built-in projects and plug-in packages.

Every piece is found through an entry-point group and named `<package>:<name>`; built-in pieces use the package
`medomni`. Finding pieces reads entry-point metadata only. A piece is imported the first time it is used.

Name clashes (R-65):

- A plug-in command that reuses a built-in command name is skipped with a warning, and the built-in runs.
- Any other two pieces with the same name in one group are both reported with an error, and neither is used.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points

BUILTIN = "medomni"

COMMANDS = "medomni.commands"  # top-level commands: Bench, Perception, Studio, plug-in commands
CHECKS = "medomni.checks"  # checks the testing kit runs
AGENTS = "medomni.agents"
DATASETS = "medomni.datasets"
TASKS = "medomni.tasks"
ENCODERS = "medomni.encoders"
TOOLS = "medomni.tools"

GROUPS = (COMMANDS, CHECKS, AGENTS, DATASETS, TASKS, ENCODERS, TOOLS)

# Commands that Core itself provides. They are not entry points, and no plug-in can replace them.
CORE_COMMANDS = ("plugins", "contracts", "cache")


class PluginError(Exception):
    """A piece could not be loaded."""


@dataclass(frozen=True)
class Piece:
    group: str
    name: str
    package: str
    target: str  # "module:attr", as written in the package's metadata

    @property
    def full_name(self) -> str:
        return f"{self.package}:{self.name}"

    @property
    def builtin(self) -> bool:
        return self.package == BUILTIN

    def load(self):
        try:
            return EntryPoint(self.name, self.target, self.group).load()
        except Exception as e:  # any import-time failure in a plug-in is reported, never raised through
            raise PluginError(f"{self.full_name}: cannot import {self.target}: {type(e).__name__}: {e}") from e


@dataclass(frozen=True)
class Resolved:
    """The pieces of one group after name clashes are settled."""

    pieces: dict[str, Piece]  # short name -> piece
    errors: tuple[tuple[Piece, str], ...]
    warnings: tuple[str, ...]


def _package(ep: EntryPoint) -> str:
    dist = getattr(ep, "dist", None)
    name = dist.metadata["Name"] if dist is not None else "unknown"
    return name.lower().replace("_", "-")


def pieces(group: str) -> list[Piece]:
    """Every piece registered in a group, without importing any of them."""
    found = {}
    for ep in entry_points(group=group):
        p = Piece(group=group, name=ep.name, package=_package(ep), target=ep.value)
        found[(p.package, p.name, p.target)] = p  # one distribution seen twice on sys.path counts once
    return sorted(found.values(), key=lambda p: (not p.builtin, p.package, p.name))


def resolve(group: str) -> Resolved:
    by_name: dict[str, list[Piece]] = {}
    for p in pieces(group):
        by_name.setdefault(p.name, []).append(p)
    ok, errors, warnings = {}, [], []
    for name, ps in by_name.items():
        builtins = [p for p in ps if p.builtin]
        if group == COMMANDS and (builtins or name in CORE_COMMANDS):
            keep = builtins[0] if builtins else None
            for p in ps:
                if not p.builtin:
                    warnings.append(f"command '{name}' from {p.package} clashes with the built-in command; "
                                    f"kept {BUILTIN}:{name}")
            if keep is not None:
                ok[name] = keep
            continue
        if len(ps) > 1:
            others = ", ".join(p.full_name for p in ps)
            for p in ps:
                errors.append((p, f"name '{name}' is registered more than once in {group} ({others}); none is loaded"))
            continue
        ok[name] = ps[0]
    return Resolved(pieces=ok, errors=tuple(errors), warnings=tuple(warnings))


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)
