"""Model card, Container API and Gateway API (Encoders and Gateway API reference pages; R-61).

The gateway's request and status models are moved here from v0.2's gateway schemas, field for field.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints, model_validator

from .base import Author, Contract, NonEmpty, Sha256, Slug

EncoderId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]+__[a-z0-9-]+$")]
Kind = Literal["labels", "events", "text", "embedding"]
Scale = Literal["probability", "logit", "score", "physical"]


class OutputDecl(Contract):
    kind: Kind
    scale: Scale | None = None
    labels: tuple[NonEmpty, ...] | None = None
    dim: int | None = Field(default=None, ge=1)


class Reliability(Contract):
    status: Literal["unmeasured", "measured"]
    evidence: str | None = None


class SourceRef(Contract):
    url: NonEmpty
    rev: str | None = None


class Weights(Contract):
    uri: NonEmpty
    sha256: Sha256 | None = None


class Runtime(Contract):
    image: NonEmpty | None = None
    digest: str | None = None


class ModelCard(Contract):
    """An encoder's `card.yaml`."""

    id: EncoderId
    family: Slug
    modality: NonEmpty
    summary: Annotated[str, StringConstraints(min_length=1, max_length=240)]
    authors: tuple[Author, ...] = Field(min_length=1)
    intended_use: str | None = None
    limits: tuple[NonEmpty, ...] = ()
    outputs: tuple[OutputDecl, ...] = Field(min_length=1)
    options: dict[str, str] = {}
    reliability: Reliability
    non_training: bool
    license: NonEmpty  # an SPDX id or expression, such as MIT AND Apache-2.0
    source: SourceRef
    weights: Weights | None = None
    runtime: Runtime | None = None
    acceptance: Literal["pending", "accepted"]

    @model_validator(mode="after")
    def _id_matches_family(self):
        if self.id.split("__", 1)[0] != self.family:
            raise ValueError(f"id {self.id} does not start with its family {self.family}")
        return self


# Container API: between the gateway and an encoder image
class ContainerRequest(Contract):
    family: Slug
    path: NonEmpty
    options: dict[str, Any] = {}


class LabelItem(Contract):
    label: NonEmpty
    value: float | int | str | bool | None
    unit: str | None = None


class LabelsBlock(Contract):
    kind: Literal["labels"]
    scale: Scale
    items: tuple[LabelItem, ...]


class EventItem(Contract):
    label: NonEmpty
    t_start: float
    t_end: float
    value: float | int | str | bool | None = None
    score: float | None = None  # optional per event (R-61)


class EventsBlock(Contract):
    kind: Literal["events"]
    items: tuple[EventItem, ...]


class TextBlock(Contract):
    kind: Literal["text"]
    text: str


class EmbeddingBlock(Contract):
    kind: Literal["embedding"]
    dim: int = Field(ge=1)
    vector: tuple[float, ...]


OutputBlock = Annotated[LabelsBlock | EventsBlock | TextBlock | EmbeddingBlock, Field(discriminator="kind")]


class ContainerResponse(Contract):
    encoder_id: EncoderId
    family: Slug
    healthy: bool
    notes: tuple[str, ...]
    outputs: tuple[OutputBlock, ...]
    runtime: dict[str, Any] | None = None


# Gateway API
class EncodeRequest(Contract):
    encoder_id: EncoderId
    path: NonEmpty
    options: dict[str, Any] = {}


class Provenance(Contract):
    input_sha256: Sha256
    input_complete: bool
    image_id: NonEmpty
    weights_sha256: Sha256 | None = None
    source_rev: str | None = None
    image: str | None = None
    image_digest: str | None = None


class EvidenceRuntime(Contract):
    container_start_ms: float = Field(ge=0)
    cached: bool
    duration_ms: float | None = Field(default=None, ge=0)


class Evidence(Contract):
    """The gateway's answer to `POST /encode`."""

    encoder_id: EncoderId
    family: Slug
    healthy: bool
    outputs: tuple[OutputBlock, ...]
    notes: tuple[str, ...]
    reliability: Reliability | None
    card: ModelCard
    provenance: Provenance
    fingerprint: Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
    runtime: EvidenceRuntime


class OutputSummary(Contract):
    kind: str | None = None
    scale: str | None = None
    dim: int | None = None
    n_labels: int | None = None


class EncoderSummary(Contract):
    id: str
    family: str | None = None
    modality: str | None = None
    summary: str = ""
    outputs: tuple[OutputSummary, ...] = ()
    runnable: bool = False
    reliability: str | None = None  # the card's reliability status
    acceptance: str | None = None
    license: str | None = None
    score: float | None = None  # match score for q, 0..1


class FamilyRow(Contract):
    family: str | None = None
    encoders: int = 0
    runnable: int = 0


class PoolSlot(Contract):
    encoder_id: str
    state: str
    inflight: int
    concurrency: int
    idle_s: float | None = None
    started_at: float | None = None
    url: str | None = None
    image_id: str | None = None
    adopted: bool | None = None


class PoolStatus(Contract):
    max_live_containers: int
    idle_timeout_s: float
    live: tuple[PoolSlot, ...]
    cache: dict[str, Any]
    call_log_failures: int = 0


class Health(Contract):
    ok: bool
    encoders: int
    live: int
    data_root: str | None = None


class Ready(Contract):
    ready: bool
    docker: bool
    data_root_ok: bool
    reasons: tuple[str, ...] = ()
