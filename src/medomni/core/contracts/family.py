"""Family registry: the schema of a family file (`core/families/<id>.yaml`) and of `aliases.yaml`.

Family files are content; only their schema is a contract (R-43).
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import Contract, NonEmpty, Slug

Format = Literal["edf", "wfdb", "dicom", "image", "omh", "table", "json-manifest"]
Dtype = Literal["int16", "uint8", "uint16", "float32", "float64", "text", "mixed"]


class Protocol(Contract):
    format: tuple[Format, ...] = Field(min_length=1)
    ndim: int = Field(ge=0)
    dtype: Dtype
    channels: tuple[NonEmpty, ...] | Annotated[int, Field(ge=1)] | None = None  # a montage, or a channel count
    roles: tuple[NonEmpty, ...] | None = None
    rate_hz: Annotated[float, Field(gt=0)] | None = None  # null: unchecked
    units: str | None = None  # null: unchecked
    range: tuple[float, float] | None = None  # [min, max] in units; null: unchecked
    # Optional keys some families need (R-59)
    axis3: str | None = None  # what the third axis of a volume is
    bands: int | None = None
    categorical: bool | None = None
    duration: str | None = None
    planes: int | None = None
    quantity: str | None = None
    schema_: str | None = Field(default=None, alias="schema")
    scope: str | None = None
    stage: str | None = None
    timing: str | None = None

    @model_validator(mode="after")
    def _range_ordered(self):
        if self.range is not None and not self.range[0] < self.range[1]:
            raise ValueError("range must be [min, max] with min < max")
        return self


class Samples(Contract):
    hf_repo: NonEmpty
    revision: NonEmpty
    dir: NonEmpty


class Retired(Contract):
    since: NonEmpty
    by: NonEmpty
    reason: NonEmpty
    ref: str | None = None


class Pending(Contract):
    since: NonEmpty
    by: NonEmpty
    question: NonEmpty
    ref: str | None = None


class OmhRecord(Contract):
    shape: str
    glucose_path: str | None = None
    time_path: str | None = None
    grid: str | None = None


class FamilyFile(Contract):
    id: Slug
    read_by: Literal["deep-encoder", "rule-extractor", "direct"]
    protocol: Protocol
    status: Literal["declared", "supplied", "deprecated"]
    samples: Samples | None = None
    samples_access: Literal["controlled"] | None = None  # a sample set exists but isn't distributed (v0.1.1)
    retired: Retired | None = None
    pending: Pending | None = None
    omh_record: OmhRecord | None = None


class AliasBlock(Contract):
    """One set of accommodations: channel and role relabels, extra rates, label prefixes, DICOM colour modes."""

    channels: dict[str, str] = {}
    roles: dict[str, str] = {}
    rates: tuple[Annotated[float, Field(gt=0)], ...] = ()
    prefixes: tuple[str, ...] = ()
    colors: tuple[str, ...] = ()


class FamilyAliases(Contract):
    accepts: tuple[NonEmpty | AliasBlock, ...] = ()  # a vocab name, or an inline block; order is kept


class AliasFile(Contract):
    """`core/families/aliases.yaml`. The order and spelling of `accepts` are part of the bridge cache key (U2.2)."""

    vocab: dict[str, AliasBlock] = {}
    families: dict[str, FamilyAliases] = {}

    @model_validator(mode="after")
    def _vocab_refs_exist(self):
        for fam, fa in self.families.items():
            for a in fa.accepts:
                if isinstance(a, str) and a not in self.vocab:
                    raise ValueError(f"family {fam} accepts unknown vocab block '{a}'")
        return self
