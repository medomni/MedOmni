"""Task template, task set, fingerprint and task proposal (Tasks reference page; R-23, R-24, R-34, R-44, R-46)."""
from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, StringConstraints, model_validator

from .base import Contract, Fingerprint, IntelligenceKind, MetricName, NonEmpty, Sha256, Slug

TemplateId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*_[a-z0-9][a-z0-9-]*$")]
_PAIR = re.compile(r"^(?P<template>[a-z0-9][a-z0-9-]*_[a-z0-9][a-z0-9-]*)(:(?P<variant>[a-z0-9-]+))?@(?P<cohort>[a-z0-9][a-z0-9-]*)$")


def _pair(v: str) -> str:
    if not _PAIR.match(v):
        raise ValueError(f"'{v}' is not <template>@<cohort> or <template>:<variant>@<cohort>")
    return v


Pair = Annotated[str, AfterValidator(_pair)]


class Author(Contract):
    name: NonEmpty
    github: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9-]+$")] | None = None  # required by the release check


class Target(Contract):
    name: Slug | Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+$")]
    label: Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]+:.+$")]  # <dataset>:<label>
    metric: MetricName  # registered in medomni.metrics (R-77)


class Environment(Contract):
    cpus: int = Field(ge=1)
    memory_mb: int = Field(ge=256)
    allow_internet: bool
    agent_timeout_sec: int = Field(ge=1)
    verifier_timeout_sec: int = Field(ge=1)


class AgentTask(Contract):
    """The part of a template only the agent kind uses: its instruction, environment and answer path."""

    instruction: NonEmpty
    environment: Environment
    submission_path: NonEmpty


class TaskTemplate(Contract):
    """`bench/datasets/<dataset>/tasks/<template>/template.yaml`."""

    template_id: TemplateId
    dataset: Slug
    authors: tuple[Author, ...] = Field(min_length=1)
    targets: tuple[Target, ...] = Field(min_length=1)
    input: dict[str, Any] = Field(min_length=1)  # tables and families the default variant stages; shape set in Stage 3
    variants: tuple[Literal["default", "full"], ...] = ("default",)
    exclude: dict[str, tuple[NonEmpty, ...]] = {}
    agent: AgentTask  # what the agent kind needs; later kinds add `llm:` or `model:` beside it (R-77)

    @model_validator(mode="after")
    def _consistent(self):
        if not self.template_id.startswith(f"{self.dataset}_"):
            raise ValueError(f"template_id {self.template_id} does not start with its dataset {self.dataset}")
        names = [t.name for t in self.targets]
        if len(names) != len(set(names)):
            raise ValueError("target names repeat")
        if "default" not in self.variants:
            raise ValueError("variants always include default")
        return self


class Step(Contract):
    name: NonEmpty
    count: int = Field(ge=0)


class CacheUse(Contract):
    key: Sha256
    content_hash: Sha256


class SetEntry(Contract):
    task: Pair
    fingerprint: Fingerprint
    steps: tuple[Step, ...] = ()
    cache: tuple[CacheUse, ...] = ()


class TaskSetCard(Contract):
    """Who publishes a task set and what it accepts, so a benchmark such as "MedOmni Bench 1.0" is a task set with a
    card, and others publish theirs the same way (R-77)."""

    version: NonEmpty
    owner: NonEmpty
    license: NonEmpty
    accepts: tuple[IntelligenceKind, ...] = Field(min_length=1)  # the intelligence kinds it may be run with


class TaskSet(Contract):
    """`bench/sets/<name>.yaml`: grow-only pins of `<template>@<cohort>` to fingerprints."""

    name: Slug
    description: str | None = None
    card: TaskSetCard | None = None
    tasks: tuple[SetEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self):
        pairs = [e.task for e in self.tasks]
        if len(pairs) != len(set(pairs)):
            raise ValueError("a pair appears twice in the task set")
        return self


class FingerprintFile(Contract):
    """A built `<template>@<cohort>`'s FINGERPRINT, as a record."""

    task: Pair
    fingerprint: Fingerprint


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
