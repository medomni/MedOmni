"""Benchmark card and task set (Tasks reference page; R-83, R-108, R-111). A task set pins task ids its builder
understands; their form is the builder's (R-142, R-147)."""
from __future__ import annotations

from pydantic import Field, model_validator

from .base import ArmName, Contract, IntelligenceKind, NonEmpty, Slug, TaskId


class SetEntry(Contract):
    """One pin: a task id at version N, and nothing else (R-108, R-111). Entries never change; a new N enters only
    a new set. Imported v0.2 sets pin version 0."""

    task: TaskId
    version: int = Field(ge=0)


class BenchmarkCard(Contract):
    """A benchmark's `benchmark.yaml`: who publishes a benchmark and what it accepts. Its task sets are in
    `sets/` beside it; records name a set `<benchmark>/<set>` (R-77, R-83)."""

    name: Slug
    description: str | None = None
    version: NonEmpty
    owner: NonEmpty
    license: NonEmpty  # covers the benchmark's own files; each dataset keeps its own licence
    accepts: tuple[IntelligenceKind, ...] = Field(min_length=1)  # the intelligence kinds it may be run with


class TaskSet(Contract):
    """A benchmark's `sets/<name>.yaml`: grow-only pins of task ids at a version, the builder that builds them, and the
    arms they are built under (R-83, R-84, R-108)."""

    name: Slug
    description: str | None = None
    builder: Slug  # the builder that builds its tasks, registered in medomni.builders (R-142)
    arms: tuple[ArmName, ...] = Field(min_length=1)
    tasks: tuple[SetEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self):
        ids = [e.task for e in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("a task appears twice in the task set")
        if len(self.arms) != len(set(self.arms)):
            raise ValueError("an arm appears twice in the task set")
        return self
