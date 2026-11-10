"""Where built tasks live (R-143 b): one tree per workspace, one content folder per task, one folder per atom."""
from __future__ import annotations

import json
from pathlib import Path

from . import TaskError

CONTENT = "_content"


def tree(ws) -> Path:
    return Path(ws.tasks) / "atomtasks"


def content_dir(tree_: Path, task: str) -> Path:
    return tree_ / CONTENT / task


def atom_dir(tree_: Path, arm: str, variant: str | None, atom: str) -> Path:
    return tree_ / arm / variant / atom if variant else tree_ / arm / atom


def read_json(tree_: Path, task: str, name: str) -> dict:
    p = content_dir(tree_, task) / name
    if not p.is_file():
        raise TaskError(f"{task}: no {name}; build the task first")
    return json.loads(p.read_text(encoding="utf-8"))


def variants(tree_: Path, task: str, arm: str) -> list[str | None]:
    """The variants a task was built under for an arm, from its manifest's config hashes (`<arm>` or `<arm>/<variant>`)."""
    keys = read_json(tree_, task, "manifest.json")["config_hash"]
    return sorted({(None if k == arm else k.split("/", 1)[1]) for k in keys if k == arm or k.startswith(arm + "/")},
                  key=lambda v: v or "")
