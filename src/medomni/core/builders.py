"""Task builders (R-142): what a builder must do so that Bench can run and score what it writes.

A builder is a Python piece in `medomni.builders`, named by its entry point. It turns task ids it understands into built
tasks in the contract's layout (`medomni.core.tasks`). How it does that, and what its inputs look like, is its own:
Core knows no recipe, template or cohort. An arm's build side for a builder is registered in `medomni.arm_builds` as
`<builder>:<arm>`; a builder refuses an arm it has no build side for (R-143, R-144).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from medomni.core import plugins

from .tasks import TaskError


class TaskBuilder(ABC):
    name: str  # registered in medomni.builders
    version: str  # goes into every config hash this builder writes

    @property
    def label(self) -> str:
        return f"{self.name}/{self.version}"

    @abstractmethod
    def config_files(self, task: str, arm: str, variant: str | None) -> dict[str, Path | bytes]:
        """The files the task's config hash covers under this arm and variant (R-111), by name."""

    @abstractmethod
    def build(self, tasks: list[str], arms: list[str], workspace) -> list[Path]:
        """Write each task's content files and its atoms under each arm in the contract's layout; return the content
        folders. Refuse, naming the task, anything it cannot build."""


def builder(name: str) -> TaskBuilder:
    pieces = plugins.resolve(plugins.BUILDERS).pieces
    if name not in pieces:
        raise TaskError(f"unknown builder '{name}' (registered: {', '.join(sorted(pieces)) or 'none'})")
    obj = pieces[name].load()
    obj = obj() if isinstance(obj, type) else obj
    if not isinstance(obj, TaskBuilder) or obj.name != name:
        raise TaskError(f"{name}: not a task builder registered under its own name")
    return obj


def arm_build(builder_name: str, arm: str):
    """An arm's build side for one builder, or None when the builder has none for it."""
    piece = plugins.resolve(plugins.ARM_BUILDS).pieces.get(f"{builder_name}:{arm}")
    return None if piece is None else piece.load()
