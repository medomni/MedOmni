"""Built tasks: what any task builder writes and Bench reads (R-142, R-143).

Core says what a built task is, never how it was made:

    <tasks>/atomtasks/
        _content/<task>/content.json    the task's atoms, targets and version (see `medomni.core.contracts.built`)
        _content/<task>/answers.csv     each atom's answer per target; never copied into an atom
        _content/<task>/manifest.json   the config hash per arm (and variant), and the builder that wrote it
        <arm>[/<variant>]/<atom>/       one atom task: task.toml, instruction.md, data/, environment/, tests/

`layout` places these folders, `sets` reads benchmarks' task sets, and `checks` holds the checks over built output
alone, which Bench runs before every run, whoever built the task. `assets` are the atom files every builder stages.
"""
from __future__ import annotations

from importlib.resources import files as _files


class TaskError(RuntimeError):
    """A task set or built task is missing or malformed; the message names it."""


def asset(*name: str) -> str:
    """One of the shared atom files: `formatcheck/format_check.py`, `formatcheck/test.sh`, `environment/Dockerfile`,
    `environment/bootstrap.sh`."""
    return _files("medomni.core.tasks").joinpath("assets", *name).read_text(encoding="utf-8")
