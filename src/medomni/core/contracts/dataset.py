"""Dataset config (`dataset.yaml`), dataset policy (`policy.yaml`) and the event table.

Fields follow the Datasets and Recipes reference pages. The event table follows R-29: MEDS columns plus a visit
column, and `FILE//<family>` rows carrying a path relative to the data root.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from .base import Contract, NonEmpty, Sha256, Slug


class Description(Contract):
    unit: NonEmpty  # what one subject is: a patient, a participant, a surgery case
    time: Literal["datetime", "visit-dates", "seconds-from-start"]
    version: NonEmpty  # the dataset release


class Units(Contract):
    table: NonEmpty
    column: NonEmpty


class HashRule(Contract):
    """Keep a subject when sha256(salt|id), as a fraction, is below `fraction` (R-32, R-41)."""

    salt: NonEmpty
    fraction: Annotated[float, Field(gt=0, le=1)]


class Reader(Contract):
    """One format reader and what it reads. The reader's own options are checked by the reader (part 6)."""

    reader: NonEmpty  # csv, omop, tree, headers, ...
    options: dict[str, Any] = {}


class DatasetConfig(Contract):
    description: Description
    units: Units
    source: Literal["all"] | HashRule  # the source population (R-52)
    read: tuple[Reader, ...] = Field(min_length=1)
    verify: dict[str, Any] = {}
    rules: dict[str, Any] = {}
    definitions: dict[str, Any] = {}  # named requirements cohorts refer to (R-89); their form is the builder's (R-147)
    converters: tuple[NonEmpty, ...] = ()  # files in the package, each exposing CONVERTER: its own family converters (R-145)
    storage_mb: int | None = Field(default=None, ge=1)  # disk an atom task's container may use; the builder's default when absent (R-145)


Permission = Literal["allow", "conditional", "deny"]


class License(Contract):
    id: NonEmpty
    url: NonEmpty


class Publish(Contract):
    schema_: Permission = Field(alias="schema")
    templates: Permission
    recipes: Permission
    id_lists: Permission
    labels: Permission
    per_record_derived: Permission
    samples: Permission


class Routes(Contract):
    local: Permission
    cloud: Permission


class Use(Contract):
    commercial: bool
    restriction: str | None = None


class DatasetPolicy(Contract):
    dataset: Slug  # matching its package folder
    version: NonEmpty
    access: Literal["open", "credentialed"]
    license: License
    modules: dict[str, License] = {}
    publish: Publish
    routes: Routes
    route_conditions: dict[str, str] = {}
    use: Use
    attribution: str | None = None
    sources: tuple[NonEmpty, ...] = Field(min_length=1)


# Event table: the Parquet columns every dataset is loaded into
EVENT_COLUMNS = ("subject_id", "time", "code", "numeric_value", "text_value", "visit_id")
FILE_COLUMNS = ("path", "sha256", "native_id")


class Event(Contract):
    """One row of the event table. Static facts have no time."""

    subject_id: NonEmpty
    time: str | None  # ISO 8601, or seconds from start for datasets whose time kind says so
    code: NonEmpty
    numeric_value: float | None = None
    text_value: str | None = None
    visit_id: str | None = None
    # FILE//<family> rows only
    path: str | None = None  # relative to the data root
    sha256: Sha256 | None = None
    native_id: str | None = None  # DICOM UID, WFDB record name


class EventTable(Contract):
    """The description of a loaded event table, written beside it."""

    dataset: NonEmpty
    description: Description
    columns: tuple[NonEmpty, ...] = EVENT_COLUMNS + FILE_COLUMNS
    rows: int = Field(ge=0)
    subjects: int = Field(ge=0)
