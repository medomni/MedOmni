"""Plug-in loading: content folders and entry points (R-2, R-65, R-69).

Content pieces (agents, datasets with their `hooks/`, tasks, encoder cards) are files. A plug-in package ships them in
one folder laid out like the repository and registers that folder with one entry point in `medomni.plugins`. The
folder is found with `importlib.util.find_spec`, which runs none of the package's code.

Python pieces (commands, checks, family converters, Studio tools) register one entry point each, in the group for their
kind. Bench, Perception and Studio register their commands in the same groups. Finding Python pieces reads
entry-point metadata only; a piece is imported the first time it is used.

Every piece is named `<package>:<name>`; built-in pieces use the package `medomni`, and built-in content is the
repository. Name clashes (R-65):

- A plug-in command that reuses a built-in command name is skipped with a warning, and the built-in runs.
- Any other two pieces of one kind with the same name are both reported with an error, and neither is used.
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from importlib.machinery import PathFinder
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path

BUILTIN = "medomni"

PLUGINS = "medomni.plugins"  # one content folder per plug-in package
COMMANDS = "medomni.commands"  # top-level commands: Bench, Perception, Studio, plug-in commands
CHECKS = "medomni.checks"  # checks the testing kit runs
CONVERTERS = "medomni.converters"  # family converters
TOOLS = "medomni.tools"  # Studio tools

GROUPS = (COMMANDS, CHECKS, CONVERTERS, TOOLS)  # groups of Python pieces

# Commands that Core itself provides. They are not entry points, and no plug-in can replace them.
CORE_COMMANDS = ("plugins", "contracts", "cache")


class PluginError(Exception):
    """A piece could not be loaded."""


def _package_of(ep: EntryPoint) -> str:
    dist = getattr(ep, "dist", None)
    name = dist.metadata["Name"] if dist is not None else "unknown"
    return name.lower().replace("_", "-")


# ---------------------------------------------------------------- Python pieces


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
    """The pieces of one group or kind after name clashes are settled."""

    pieces: dict  # short name -> Piece or Content
    errors: tuple  # (piece, message)
    warnings: tuple[str, ...]


def pieces(group: str) -> list[Piece]:
    """Every Python piece registered in a group, without importing any of them."""
    found = {}
    for ep in entry_points(group=group):
        p = Piece(group=group, name=ep.name, package=_package_of(ep), target=ep.value)
        found[(p.package, p.name, p.target)] = p  # one distribution seen twice on sys.path counts once
    return sorted(found.values(), key=lambda p: (not p.builtin, p.package, p.name))


def _settle(kind: str, found: list, commands: bool = False) -> Resolved:
    by_name: dict[str, list] = {}
    for p in found:
        by_name.setdefault(p.name, []).append(p)
    ok, errors, warnings = {}, [], []
    for name, ps in by_name.items():
        builtins = [p for p in ps if p.builtin]
        if commands and (builtins or name in CORE_COMMANDS):
            for p in ps:
                if not p.builtin:
                    warnings.append(f"command '{name}' from {p.package} clashes with the built-in command; "
                                    f"kept {BUILTIN}:{name}")
            if builtins:
                ok[name] = builtins[0]
            continue
        if len(ps) > 1:
            others = ", ".join(p.full_name for p in ps)
            for p in ps:
                errors.append((p, f"name '{name}' is registered more than once in {kind} ({others}); none is loaded"))
            continue
        ok[name] = ps[0]
    return Resolved(pieces=ok, errors=tuple(errors), warnings=tuple(warnings))


def resolve(group: str) -> Resolved:
    return _settle(group, pieces(group), commands=group == COMMANDS)


# ---------------------------------------------------------------- content folders


@dataclass(frozen=True)
class Folder:
    """A plug-in package's content folder, or why it could not be found."""

    package: str
    name: str
    target: str  # "<module>:<folder>": a folder inside the module's package directory
    path: Path | None
    error: str | None = None


def locate(target: str) -> Path:
    """The folder a `medomni.plugins` target points at, found without importing the package."""
    module, sep, sub = target.partition(":")
    if not sep or not module or not sub or "/" in sub or sub in (".", ".."):
        raise PluginError(f"target '{target}' must be '<module>:<folder>'")
    parts = module.split(".")
    spec = importlib.util.find_spec(parts[0])  # a top-level name: nothing is imported
    for part in parts[1:]:  # walk sub-packages by path, so their parents are not imported either
        locations = spec.submodule_search_locations if spec else None
        spec = PathFinder.find_spec(part, list(locations)) if locations else None
    if spec is None or spec.submodule_search_locations is None:
        raise PluginError(f"target '{target}': no package '{module}' installed")
    for loc in spec.submodule_search_locations:
        d = Path(loc) / sub
        if d.is_dir():
            return d
        if not Path(loc).is_dir():
            raise PluginError(f"target '{target}': '{module}' is not a folder on disk (zip installs are not "
                              "supported; install a wheel or in editable mode)")
    raise PluginError(f"target '{target}': no folder '{sub}' in package '{module}'")


def folders() -> list[Folder]:
    """Every installed plug-in content folder. Runs none of the plug-ins' code."""
    found = {}
    for ep in entry_points(group=PLUGINS):
        package = _package_of(ep)
        try:
            f = Folder(package, ep.name, ep.value, locate(ep.value))
        except PluginError as e:
            f = Folder(package, ep.name, ep.value, None, f"{package}:{ep.name}: {e}")
        found[(package, ep.name, ep.value)] = f
    return sorted(found.values(), key=lambda f: (f.package, f.name))


@dataclass(frozen=True)
class Kind:
    name: str
    marker: str  # glob, under a content root, for the file that marks one piece
    depth: int  # how far up from the marker the piece's root is (0: the marker itself)

    def piece_name(self, root: Path) -> str:
        return f"{root.parent.name}__{root.name}" if self.name == "encoders" else root.stem


KINDS = (
    Kind("agents", "bench/agents/*.yaml", 0),
    Kind("datasets", "bench/datasets/*/dataset.yaml", 1),
    Kind("tasks", "bench/datasets/*/tasks/*/template.yaml", 1),
    Kind("encoders", "perception/encoders/*/*/card.yaml", 1),
)


@dataclass(frozen=True)
class Content:
    """One content piece: an agent file, or a dataset, task or encoder folder."""

    kind: str
    name: str
    package: str
    path: Path  # the agent file, or the piece's folder

    @property
    def full_name(self) -> str:
        return f"{self.package}:{self.name}"

    @property
    def builtin(self) -> bool:
        return self.package == BUILTIN


def roots(repo: Path | None) -> tuple[list[tuple[str, Path]], list[Folder]]:
    """Content roots, repository first: [(package, folder)], and the plug-in folders that could not be found."""
    found = [(BUILTIN, repo)] if repo is not None else []
    bad = []
    for f in folders():
        (found.append((f.package, f.path)) if f.path is not None else bad.append(f))
    return found, bad


def content(roots: list[tuple[str, Path]]) -> dict[str, Resolved]:
    """Every content piece under the roots, by kind, after name clashes are settled."""
    out = {}
    for kind in KINDS:
        found = []
        for package, root in roots:
            for marker in sorted(root.glob(kind.marker)):
                piece_root = marker
                for _ in range(kind.depth):
                    piece_root = piece_root.parent
                found.append(Content(kind.name, kind.piece_name(piece_root), package, piece_root))
        out[kind.name] = _settle(kind.name, found)
    return out


def find_repo(start: Path | None = None) -> Path | None:
    """The MedOmni repository containing `start` (default: the current folder), or None."""
    p = (start or Path.cwd()).resolve()
    for d in (p, *p.parents):
        f = d / "pyproject.toml"
        if f.is_file() and 'name = "medomni"' in f.read_text(encoding="utf-8"):
            return d
    return None


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)
