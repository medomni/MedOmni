"""R-145: Core's code and data name no dataset, benchmark, arm, runner or project folder. Content and execution meet
only at contracts. Beside the import rule (`test_import_rule.py`)."""
import ast
import re
from pathlib import Path

from medomni.core import plugins
from medomni.core.contracts.base import IntelligenceKind
from medomni.core.loading import dataset_packages
from medomni.core.tasks.sets import benchmark_folders
from typing import get_args

CORE = Path(__file__).resolve().parents[2] / "src/medomni/core"
# Core's own dummy data, and the shared atom files, which stay byte-identical to v0.2's for the reproduction check (check 3)
EXEMPT = ("testing/", "families/dummy/", "tasks/assets/")


def names() -> tuple[set[str], set[str]]:
    """(names matched anywhere, names matched as a whole string literal), from what is installed."""
    anywhere = {p.name for p in dataset_packages() if CORE not in p.parents} | set(benchmark_folders())
    for piece in plugins.pieces(plugins.RUNNERS):  # a runner's module, such as the agent runner's
        anywhere.add(piece.target.split(":")[0].rsplit(".", 1)[-1])
    anywhere -= {"runs"}  # the module holding the runner interface itself
    literal = set(plugins.arm_names()) | ({p.name for p in plugins.pieces(plugins.RUNNERS)} - set(get_args(IntelligenceKind)))
    return anywhere, literal


def files():
    for f in sorted(CORE.rglob("*")):
        rel = f.relative_to(CORE).as_posix()
        if f.is_file() and "__pycache__" not in rel and not rel.startswith(EXEMPT):
            yield rel, f


def test_core_names_no_content_and_no_runner():
    anywhere, literal = names()
    assert anywhere and literal  # the names really come from what is installed
    word = re.compile(r"(?i)(?<![a-z0-9-])(" + "|".join(re.escape(n) for n in sorted(anywhere, key=len, reverse=True)) + r")(?![a-z0-9])")
    folder = re.compile(r"(?<![a-z0-9_./-])(bench|studio|perception)/")
    found = []
    for rel, f in files():
        text = f.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            found += [f"{rel}:{i}: names {m.group(0)}" for m in word.finditer(line)]
            found += [f"{rel}:{i}: names the project folder {m.group(0)}" for m in folder.finditer(line)]
        if f.suffix == ".py":
            found += [f"{rel}:{n.lineno}: names {n.value!r}" for n in ast.walk(ast.parse(text))
                      if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in literal]
    assert found == []


def test_the_guard_catches_a_planted_name(tmp_path):
    anywhere, _ = names()
    planted = next(iter(sorted(anywhere)))
    word = re.compile(r"(?i)(?<![a-z0-9-])" + re.escape(planted) + r"(?![a-z0-9])")
    assert word.search(f"# load {planted.upper()} here") and not word.search(f"x{planted}y")
