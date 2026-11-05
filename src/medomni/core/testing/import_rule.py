"""The import rule: which project may import which.

Core imports only Core. Bench and Perception import Core and themselves. Studio imports Core, Bench and itself.
No module edits `sys.path`. The check reads source files with the standard library's `ast`; it imports nothing.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

PROJECTS = ("core", "bench", "perception", "studio")

RULES: dict[str, frozenset[str]] = {
    "core": frozenset({"core"}),
    "bench": frozenset({"core", "bench"}),
    "perception": frozenset({"core", "perception"}),
    "studio": frozenset({"core", "bench", "studio"}),
}


@dataclass(frozen=True)
class Violation:
    path: str  # relative to the package root's parent, e.g. medomni/core/x.py
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _module(rel: Path) -> list[str]:
    parts = list(rel.with_suffix("").parts)
    return parts[:-1] if parts[-1] == "__init__" else parts


def _project(mod: list[str]) -> str | None:
    """`medomni.<project>...` -> project; the top-level `medomni` package counts as Core."""
    if not mod or mod[0] != "medomni":
        return None
    if len(mod) == 1:
        return "core"
    return mod[1] if mod[1] in PROJECTS else f"<unknown:{mod[1]}>"


def _edits_sys_path(node: ast.AST) -> bool:
    def is_sys_path(n):
        return isinstance(n, ast.Attribute) and n.attr == "path" and isinstance(n.value, ast.Name) and n.value.id == "sys"

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and is_sys_path(node.func.value):
        return node.func.attr in ("insert", "append", "extend", "remove", "pop", "clear")
    if isinstance(node, (ast.Assign, ast.AugAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return any(is_sys_path(t) or (isinstance(t, ast.Subscript) and is_sys_path(t.value)) for t in targets)
    return False


def check_file(path: Path, root: Path) -> list[Violation]:
    rel = path.relative_to(root)
    mod = _module(rel)
    src = _project(mod)
    shown = str(rel)
    if src is None or src.startswith("<"):
        return [Violation(shown, 1, f"file is outside the projects {PROJECTS}")]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package = mod if path.name == "__init__.py" else mod[:-1]
    out = []
    for node in ast.walk(tree):
        targets: list[list[str]] = []
        if isinstance(node, ast.Import):
            targets = [a.name.split(".") for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                up = node.level - 1
                if up >= len(package):
                    out.append(Violation(shown, node.lineno, "relative import climbs out of the medomni package"))
                    continue
                target = package[: len(package) - up] + (node.module.split(".") if node.module else [])
            else:
                target = node.module.split(".")
            # `from medomni import bench` (or `from .. import bench`) imports a project, so the name is the target;
            # `from medomni import __version__` takes a name from the top-level package, which counts as Core
            if len(target) >= 2:
                targets = [target]
            else:
                targets = [target + [a.name] if a.name in PROJECTS else target for a in node.names]
        elif _edits_sys_path(node):
            out.append(Violation(shown, node.lineno, "edits sys.path"))
        for t in targets:
            dst = _project(t)
            if dst is None:
                continue  # standard library or third party
            if dst not in RULES.get(src, frozenset()):
                out.append(Violation(shown, node.lineno, f"{src} imports {'.'.join(t)} ({dst})"))
    return out


def check_tree(package_dir: Path) -> list[Violation]:
    """Check every .py file under a `medomni` package folder (such as src/medomni)."""
    package_dir = Path(package_dir)
    root = package_dir.parent
    out = []
    for path in sorted(package_dir.rglob("*.py")):
        out += check_file(path, root)
    return out
