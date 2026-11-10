"""Recipe: the cohort file, the label library and the evidence file (Recipes reference page; R-26 to R-28, R-42, R-47).

These models check each file's fields. Checks across files (a cohort naming an unknown label) are in
`medomni.core.recipes` (Stage 2, part 6). Running a recipe is Build's job, in Bench.
"""
from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, ConfigDict, Field, RootModel, model_validator

from .base import Contract, NonEmpty, Slug, Version

_OFFSET = r"(anchor|anchor\.event|visit:[^\s]+)(\s*[+-]\s*\d+(\.\d+)?\s*(minutes|hours|days))?"
_TIME = re.compile(rf"^({_OFFSET}|any)$")


def _time(v: str) -> str:
    if not _TIME.match(v.strip()):
        raise ValueError(f"'{v}' is not a time: use anchor, anchor.event, visit:<code>, an offset such as "
                         f"'anchor - 24 hours', or any")
    return v


Time = Annotated[str, AfterValidator(_time)]


class Window(Contract):
    from_: Time | None = Field(default=None, alias="from")
    to: Time | None = None
    include_from: bool = True
    include_to: bool = True


# Requirements: exactly one form per entry
class Any_(Window):
    any: tuple[NonEmpty, ...] = Field(min_length=1)
    same_visit: bool = False


class None_(Window):
    none: tuple[NonEmpty, ...] = Field(min_length=1)
    same_visit: bool = False


class Files(Window):
    files: tuple[Slug, ...] = Field(min_length=1)
    same_visit: bool = False


class HasLabel(Contract):
    has_label: NonEmpty


class ConvertsRule(Contract):
    min_families: int = Field(ge=1)


class Converts(Contract):
    """At least `min_families` of the patient's files convert and match their family (S1's BDSP recipes). Checked in
    draw order, and a patient who fails is replaced by the next (Build page, file check)."""

    converts: ConvertsRule
    when: Literal["select"] = "select"


class Definition(Contract):
    definition: NonEmpty  # a definition named in dataset.yaml's `definitions` (R-89)


Requirement = Any_ | None_ | Files | HasLabel | Definition | Converts


class SourceFraction(Contract):
    fraction: Annotated[float, Field(gt=0, le=1)] | None = None  # omitted: the dataset's default


class Anchor(Contract):
    event: NonEmpty
    pick: Literal["first", "last"] = "first"
    plus: str | None = None  # an offset, such as '24 hours'


class Select(Contract):
    n: int = Field(ge=1)
    by: tuple[NonEmpty, ...] = ()  # target names that define the classes; empty for a continuous target
    balance: tuple[NonEmpty, ...] = ()  # labels of the library that split each class further; never scored or shown
    seed: int | NonEmpty  # hashed into the rank (R-36), so text works as well as a number


class Cohort(Contract):
    """`tasks/<template>/cohorts/<cohort>.yaml`."""

    version: Version  # the pair's version N.X (R-106); a template-wide change bumps every cohort of the template
    source: Literal["all"] | SourceFraction
    anchor: Anchor
    require: tuple[Requirement, ...] = ()
    select: Select


class CohortTestPatient(Contract):
    events: tuple[dict[str, Any], ...]
    expect: dict[str, Any]

    @model_validator(mode="after")
    def _expect_in(self):
        if not isinstance(self.expect.get("in"), bool):
            raise ValueError("expect.in must be true or false")
        return self


class CohortTests(Contract):
    """`cohorts/<cohort>.tests.yaml`: test patients."""

    patients: tuple[CohortTestPatient, ...] = Field(min_length=1)


class Guard(Contract):
    codes: tuple[NonEmpty, ...] = ()
    fields: tuple[NonEmpty, ...] = ()


class Case(Contract):
    when: dict[str, Any]
    then: int | float | str


class Label(Window):
    """One entry of `labels.yaml`. `from` and `to` are required; `any` marks a label read from any time."""

    exists: NonEmpty | None = None
    none: NonEmpty | None = None  # 1 when no matching code occurs in the window, else 0
    value: NonEmpty | None = None
    pick: Literal["first", "last", "min", "max"] = "last"
    op: Literal["<", "<=", "==", ">=", ">"] | None = None
    x: float | None = None
    bins: tuple[float, ...] | None = None
    cases: tuple[Case, ...] | None = None
    else_: int | float | str | None = Field(default=None, alias="else")
    default: int | float | str | None = None
    hook: NonEmpty | None = None
    question: NonEmpty | None = None  # the sentence that tells the agent exactly what this target asks
    same_visit: bool = False  # only events in the anchor's visit count
    other_visit: bool = False  # only events in another visit count (readmission)
    guard: Guard = Guard()

    @model_validator(mode="after")
    def _one_rule(self):
        if self.from_ is None or self.to is None:
            raise ValueError("a label needs both from and to ('any' for a label read from any time)")
        kinds = [k for k in ("exists", "none", "value", "cases", "hook") if getattr(self, k) is not None]
        if len(kinds) != 1:
            raise ValueError(f"a label has exactly one of exists, none, value, cases, hook (found {kinds or 'no rule'})")
        if self.same_visit and self.other_visit:
            raise ValueError("same_visit and other_visit exclude each other")
        if (self.op is None) != (self.x is None):
            raise ValueError("op and x go together")
        if self.value is None and (self.op or self.bins):
            raise ValueError("op, x and bins apply to a value label")
        return self


class LabelLibrary(RootModel[dict[NonEmpty, Label]]):
    """A dataset package's `labels.yaml`: label name -> rule. Templates name `<dataset>:<label>`."""

    model_config = ConfigDict(frozen=True, strict=True)

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.root:
            raise ValueError("a label library has at least one label")
        return self


class TimeFrom(Contract):
    table: NonEmpty
    key: NonEmpty
    column: NonEmpty


# A guard reference: the fields of the guards of the template's labels (R-47)
GuardFields = Literal["guard.fields"]


class KeepIfKept(Contract):
    table: NonEmpty
    key: NonEmpty


class TableRule(Contract):
    time: str | None = None
    time_from: TimeFrom | None = None
    missing_time: Literal["drop", "keep"] = "keep"
    visit: str | None = None
    skip_index_visit: bool = False
    end: str | None = None
    blank_after_end: tuple[NonEmpty, ...] = ()
    missing_end: Literal["after", "before"] = "after"
    blank_in_index_visit: tuple[NonEmpty, ...] | GuardFields = ()
    drop: Literal["guard"] | None = None  # drop rows whose emitted code matches a guard code of the template's labels
    keep_if_kept: KeepIfKept | None = None
    write_empty: bool = False


class Static(Contract):
    blank: tuple[NonEmpty, ...] | GuardFields = ()
    aliases: dict[str, NonEmpty | tuple[NonEmpty, ...]] = {}  # a static field and the column (or columns) holding it


class EvidenceRules(Contract):
    """A dataset package's `evidence.yaml`."""

    tables: dict[NonEmpty, TableRule] = {}
    static: Static = Static()
    files: dict[str, Any] = {}
    reading_note: str | None = None  # a fact about reading this dataset's files, told to the agent in every arm
    views: NonEmpty | None = None  # a package hook giving the agent-facing forms: demographics, measurements, file_meta
