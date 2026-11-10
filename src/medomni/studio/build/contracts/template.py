"""Task template (Tasks reference page; R-23, R-24, R-34, R-44, R-46, R-106, R-109): the v1 builder's own format
(R-142, R-147). The v1 builder's task id is `<template>@<cohort>` or `<template>:<evidence>@<cohort>`."""
from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, StringConstraints, model_validator

from medomni.core.contracts.base import Author, Contract, MetricName, NonEmpty, Slug

TemplateId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*_[a-z0-9][a-z0-9-]*$")]
_PAIR = re.compile(r"^(?P<template>[a-z0-9][a-z0-9-]*_[a-z0-9][a-z0-9-]*)(:(?P<evidence>[a-z0-9-]+))?@(?P<cohort>[a-z0-9][a-z0-9-]*)$")


def _pair(v: str) -> str:
    if not _PAIR.match(v):
        raise ValueError(f"'{v}' is not <template>@<cohort> or <template>:<evidence>@<cohort>")
    return v


Pair = Annotated[str, AfterValidator(_pair)]


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
