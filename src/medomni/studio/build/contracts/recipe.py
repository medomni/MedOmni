"""Recipe: the cohort file, the label library and the evidence file (Recipes reference page; R-26 to R-28, R-42, R-47).

These models check each file's fields. Checks across files (a cohort naming an unknown label) are in
`medomni.core.recipes` (Stage 2, part 6). Running a recipe is Build's job, in Bench.
"""
from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, ConfigDict, Field, RootModel, model_validator

from .base import Contract, NonEmpty, Slug

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


class Condition(Contract):
    condition: NonEmpty


Requirement = Any_ | None_ | Files | HasLabel | Condition


class SourceFraction(Contract):
    fraction: Annotated[float, Field(gt=0, le=1)] | None = None  # omitted: the dataset's default


class Anchor(Contract):
    event: NonEmpty
    pick: Literal["first", "last"] = "first"
    plus: str | None = None  # an offset, such as '24 hours'


class Draw(Contract):
    n: int = Field(ge=1)
    by: tuple[NonEmpty, ...] = Field(min_length=1)
    seed: int


class Cohort(Contract):
    """`tasks/<template>/cohorts/<cohort>.yaml`."""

    source: Literal["all"] | SourceFraction
    anchor: Anchor
    require: tuple[Requirement, ...] = ()
    draw: Draw


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
    value: NonEmpty | None = None
    pick: Literal["first", "last", "min", "max"] = "last"
    op: Literal["<", "<=", "==", ">=", ">"] | None = None
    x: float | None = None
    bins: tuple[float, ...] | None = None
    cases: tuple[Case, ...] | None = None
    else_: int | float | str | None = Field(default=None, alias="else")
    default: int | float | str | None = None
    hook: NonEmpty | None = None
    guard: Guard = Guard()

    @model_validator(mode="after")
    def _one_rule(self):
        if self.from_ is None or self.to is None:
            raise ValueError("a label needs both from and to ('any' for a label read from any time)")
        kinds = [k for k in ("exists", "value", "cases", "hook") if getattr(self, k) is not None]
        if len(kinds) != 1:
            raise ValueError(f"a label has exactly one of exists, value, cases, hook (found {kinds or 'none'})")
        if (self.op is None) != (self.x is None):
            raise ValueError("op and x go together")
        if self.value is None and (self.op or self.bins):
            raise ValueError("op, x and bins apply to a value label")
        return self


class LabelLibrary(RootModel[dict[NonEmpty, Label]]):
    """`bench/datasets/<dataset>/labels.yaml`: label name -> rule. Templates name `<dataset>:<label>`."""

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


class Drop(Contract):
    columns: tuple[NonEmpty, ...] = Field(min_length=1)
    split: str | None = None
    strip: str | None = None


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
    blank_in_index_visit: tuple[NonEmpty, ...] = ()
    drop: Drop | None = None
    keep_if_kept: KeepIfKept | None = None
    write_empty: bool = False


class Static(Contract):
    blank: tuple[NonEmpty, ...] = ()
    aliases: dict[str, str] = {}


class EvidenceRules(Contract):
    """`bench/datasets/<dataset>/evidence.yaml`."""

    tables: dict[NonEmpty, TableRule] = {}
    static: Static = Static()
    files: dict[str, Any] = {}
