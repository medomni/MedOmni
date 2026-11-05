"""Agent config, cache entry, result record and workspace config."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, model_validator

from .base import Contract, EnvRef, Fingerprint, NonEmpty, Sha256, Slug
from .task import Pair


class AgentConfig(Contract):
    """`bench/agents/<name>.yaml` (Run your agent guide)."""

    name: Slug
    scaffold: NonEmpty  # a Harbor agent, such as terminus-2
    model: NonEmpty
    route: Literal["local", "cloud"]
    model_served: NonEmpty | tuple[NonEmpty, ...]  # what the provider reports back; some report two spellings
    env: dict[str, str] = {}
    max_turns: int | None = Field(default=None, ge=1)
    api_base: str | None = None

    @model_validator(mode="after")
    def _keys_by_reference(self):
        if self.route == "cloud":
            import re

            bad = [k for k, v in self.env.items() if not re.match(r"^\$\{[A-Z][A-Z0-9_]*\}$", v)]
            if bad:
                raise ValueError(f"a cloud agent names keys only as ${{VARNAME}}; literal values in {bad}")
        return self


class CacheInput(Contract):
    name: NonEmpty  # a raw file (relative to the data root) or another entry (<dataset>/<step>/<key>)
    hash: Sha256


class CacheEntry(Contract):
    """`<workspace>/cache/<dataset>/<step>/<key>/CACHE.json`."""

    dataset: Slug
    step: Slug
    version: NonEmpty
    key: Sha256
    params: dict[str, Any] = {}
    inputs: tuple[CacheInput, ...] = ()
    rows: dict[str, int] = {}
    content_hash: Sha256
    release: NonEmpty  # the MedOmni release that wrote it


class EncoderServed(Contract):
    id: NonEmpty
    image_digest: NonEmpty


class RunRecord(Contract):
    kind: Literal["run"]
    run_id: NonEmpty
    release: NonEmpty
    task_set: Slug
    task: Pair
    agent: Slug
    condition: Literal["enc", "noenc", "enc-forced"] | Annotated[str, AfterValidator(lambda v: _ladder(v))]
    fingerprint: Fingerprint
    fingerprint_match: bool
    model_served: str | None
    encoders_served: tuple[EncoderServed, ...] = ()
    encoder_calls: dict[str, int] = {}
    files_opened: tuple[str, ...] = ()
    error_kind: str | None = None
    api_cost: float | None = Field(default=None, ge=0)


def _ladder(v: str) -> str:
    if not v.startswith("ladder"):
        raise ValueError(f"unknown condition {v}")
    return v


class ScoreRecord(Contract):
    kind: Literal["score"]
    run_id: NonEmpty
    release: NonEmpty
    task_set: Slug
    task_set_hash: Sha256
    target: NonEmpty
    fingerprint: Fingerprint
    n_atoms: int = Field(ge=0)
    n_failed: int = Field(ge=0)
    metric: Literal["auc", "qwk", "mae"]
    value: float | None
    flags: tuple[str, ...] = ()
    encoder_use: dict[str, Any] = {}


ResultRecord = Annotated[RunRecord | ScoreRecord, Field(discriminator="kind")]


def _absolute(v: str) -> str:
    if not PurePosixPath(v).is_absolute():
        raise ValueError(f"'{v}' is not an absolute path")
    return v


AbsPath = Annotated[str, AfterValidator(_absolute)]


class DatasetPath(Contract):
    path: AbsPath


class WorkspaceConfig(Contract):
    """`<workspace>/workspace.yaml`: where your copies, cache, built tasks, runs and results are (U2.7, R-60)."""

    datasets: dict[Slug, DatasetPath] = {}
    cache: AbsPath
    tasks: AbsPath
    runs: AbsPath
    results: AbsPath
    deployment: dict[str, Any] = {}  # the encoder set (R-60)
    keys_file: AbsPath
    hf_cache: AbsPath | None = None
    scratch: AbsPath | None = None
