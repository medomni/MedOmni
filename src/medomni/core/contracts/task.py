"""Task template, benchmark card, task set and task proposal (Tasks reference page; R-23, R-24, R-34, R-44, R-46, R-83,
R-106 to R-109, R-111)."""
from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, StringConstraints, model_validator

from .base import ArmName, Contract, IntelligenceKind, MetricName, NonEmpty, Slug

TemplateId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*_[a-z0-9][a-z0-9-]*$")]
_PAIR = re.compile(r"^(?P<template>[a-z0-9][a-z0-9-]*_[a-z0-9][a-z0-9-]*)(:(?P<evidence>[a-z0-9-]+))?@(?P<cohort>[a-z0-9][a-z0-9-]*)$")


def _pair(v: str) -> str:
    if not _PAIR.match(v):
        raise ValueError(f"'{v}' is not <template>@<cohort> or <template>:<evidence>@<cohort>")
    return v


Pair = Annotated[str, AfterValidator(_pair)]


class Author(Contract):
    name: NonEmpty
    github: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9-]+$")] | None = None  # required by the release check


class Target(Contract):
    name: Slug | Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+$")]
    label: Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]+:.+$")]  # <dataset>:<label>
    metric: MetricName  # registered in medomni.metrics (R-77)
    question: NonEmpty | None = None  # replaces the label's `question` when this template asks it differently


class Environment(Contract):
    cpus: int = Field(ge=1)
    memory_mb: int = Field(ge=256)
    allow_internet: bool
    agent_timeout_sec: int = Field(ge=1)
    verifier_timeout_sec: int = Field(ge=1)


class AgentTask(Contract):
    """The part of a template only the agent kind uses: its clinical question, instruction, environment and answer
    path. `statement` is the question alone; the renderer opens every atom's instruction with it (U2.9)."""

    statement: NonEmpty
    instruction: NonEmpty
    environment: Environment
    submission_path: NonEmpty


class FullEvidence(Contract):
    """What the `full` evidence variant stages differently from `default`: its own `input` and `exclude`, each
    replacing the template's when given (v0.2's `-full` twins that overrode them)."""

    input: dict[str, Any] | None = None
    exclude: dict[str, tuple[NonEmpty, ...]] | None = None


class TaskTemplate(Contract):
    """A dataset package's `tasks/<template>/template.yaml`."""

    template_id: TemplateId
    dataset: Slug
    authors: tuple[Author, ...] = Field(min_length=1)
    targets: tuple[Target, ...] = Field(min_length=1)
    input: dict[str, Any] = Field(min_length=1)  # what the default evidence stages; read by Build (Stage 3 part 3)
    evidence: tuple[Literal["default", "full"], ...] = ("default",)  # evidence variants; each is its own task (R-109)
    exclude: dict[str, tuple[NonEmpty, ...]] = {}
    full: FullEvidence | None = None  # the full variant's own input or exclude, when they differ from default's
    agent: AgentTask  # what the agent kind needs; later kinds add `llm:` or `model:` beside it (R-77)

    @model_validator(mode="after")
    def _consistent(self):
        if not self.template_id.startswith(f"{self.dataset}_"):
            raise ValueError(f"template_id {self.template_id} does not start with its dataset {self.dataset}")
        names = [t.name for t in self.targets]
        if len(names) != len(set(names)):
            raise ValueError("target names repeat")
        if "default" not in self.evidence:
            raise ValueError("evidence always includes default")
        if self.full is not None and "full" not in self.evidence:
            raise ValueError("full: is given but evidence lists no full variant")
        return self


class SetEntry(Contract):
    """One pin: a pair, with its evidence variant, at version N, and nothing else (R-108, R-111). Entries never
    change; a new N enters only a new set. Imported v0.2 sets pin version 0."""

    task: Pair
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
    """A benchmark's `sets/<name>.yaml`: grow-only pins of pairs at a version, the builder that builds them, and the
    arms they are built under (R-83, R-84, R-108)."""

    name: Slug
    description: str | None = None
    builder: Slug  # the builder that builds its tasks, registered in medomni.builders (R-142)
    arms: tuple[ArmName, ...] = Field(min_length=1)
    tasks: tuple[SetEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self):
        pairs = [e.task for e in self.tasks]
        if len(pairs) != len(set(pairs)):
            raise ValueError("a pair appears twice in the task set")
        if len(self.arms) != len(set(self.arms)):
            raise ValueError("an arm appears twice in the task set")
        return self


class TaskProposal(Contract):
    """One proposed task and its review state (Studio). The draft becomes a frozen template when signed off."""

    title: NonEmpty
    by: NonEmpty
    org: str | None = None
    at: NonEmpty
    mode: NonEmpty
    state: Literal["draft", "under-review", "signed-off", "frozen"]
    dataset: Slug | None = None
    draft: dict[str, Any] = {}
