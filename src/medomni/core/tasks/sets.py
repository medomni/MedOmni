"""Benchmarks' task sets (R-83, R-108, R-111, R-143 b): read a set and its `task_set_hash`.

A set entry pins a task and its version N, nothing else. A set's benchmark card and the set files are found where a
project's `benchmarks` content kind says (R-145).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from medomni.core import plugins
from medomni.core.contracts import BenchmarkCard, TaskSet, load

from . import TaskError


def benchmark_folders() -> dict[str, Path]:
    """{benchmark name: folder}, the repository's and every plug-in's."""
    found = plugins.content(plugins.roots(plugins.find_repo())[0])
    return {name: piece.path for name, piece in found["benchmarks"].pieces.items()}


def load_set(name: str) -> tuple[TaskSet, Path]:
    bench, _, sname = name.partition("/")
    folders = benchmark_folders()
    if not sname or bench not in folders:
        raise TaskError(f"no benchmark for '{name}' (write <benchmark>/<set>; found: {', '.join(sorted(folders))})")
    path = folders[bench] / "sets" / f"{sname}.yaml"
    if not path.is_file():
        raise TaskError(f"no task set {name} at {path}")
    load(folders[bench] / "benchmark.yaml", BenchmarkCard)
    return load(path, TaskSet), path


def task_set_hash(task_set: TaskSet) -> str:
    """sha256 over the set's pins in order of task: the tasks and their N, nothing else."""
    lines = sorted(f"{e.task}\t{e.version}" for e in task_set.tasks)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def all_sets() -> list[tuple[str, TaskSet]]:
    out = []
    for bench, folder in sorted(benchmark_folders().items()):
        for p in sorted((folder / "sets").glob("*.yaml")):
            out.append((f"{bench}/{p.stem}", load(p, TaskSet)))
    return out
