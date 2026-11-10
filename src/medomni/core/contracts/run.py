"""Agent config, cache entry, result record, prediction record and workspace config."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, model_validator

from .base import (ArmName, ConfigHash, Contract, IntelligenceKind, IntelligenceRef, MetricName, NonEmpty, Sha256,
                   Slug, TaskId, TaskSetRef, Version)


class AgentConfig(Contract):
    """An agent config (Run your agent guide): an intelligence of kind `agent` (R-76). What the runner needs beyond the
    model is in `settings`, which that runner owns and checks (R-145); Core reads none of it."""

    kind: IntelligenceKind = "agent"
    name: Slug
    model: NonEmpty
    route: Literal["local", "cloud"]  # where the model runs; dataset policies list the routes they allow (no run checks it yet)
    runner: Slug | None = None  # a runner other than the kind's own, such as a replay with no model
    settings: dict[str, Any] = {}


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


class AgentRun(Contract):
    """What only the agent runner records: the arm and how the agent used encoders and files (R-76, R-84)."""

    arm: ArmName  # checked exactly against `medomni.arms`; Bench checks `arm_variant` against the arm (R-85)
    arm_variant: Slug | None = None  # e.g. the ladder's rungs r1 to r6
    encoders_served: tuple[EncoderServed, ...] = ()
    encoder_calls: dict[str, int] = {}
    files_opened: tuple[str, ...] = ()


class RunRecord(Contract):
    kind: Literal["run"]
    run_id: NonEmpty
    release: NonEmpty
    task_set: TaskSetRef
    task: TaskId
    task_version: Version
    config_hash: ConfigHash  # from the build manifest (R-111)
    intelligence: IntelligenceRef
    model_served: str | None
    error_kind: str | None = None
    api_cost: float | None = Field(default=None, ge=0)
    agent: AgentRun | None = None  # the agent runner's block; present exactly when the kind is agent

    @model_validator(mode="after")
    def _runner_block(self):
        if (self.intelligence.kind == "agent") != (self.agent is not None):
            raise ValueError("a run of an agent has an `agent` block, and only such a run")
        _imported(self.config_hash, self.task_version)
        return self


def _imported(config_hash: str, task_version: str) -> None:
    """A `v0.2:` stand-in belongs to an imported v0.2 record, which is version 0.0 (R-90, R-106, R-111)."""
    if config_hash.startswith("v0.2:") != (task_version == "0.0"):
        raise ValueError("a `v0.2:` config hash goes with task_version 0.0 (an imported v0.2 record), and only there")


class ScoreRecord(Contract):
    kind: Literal["score"]
    run_id: NonEmpty
    release: NonEmpty
    task_set: TaskSetRef
    task_set_hash: Sha256
    target: NonEmpty
    task_version: Version
    config_hash: ConfigHash  # one score has one config hash; runs that differ inside it are refused (R-114)
    arm: ArmName | None = None  # the arm the scored runs ran under, for kinds that have arms
    arm_variant: Slug | None = None
    n_atoms: int = Field(ge=0)
    n_failed: int = Field(ge=0)
    intelligence: IntelligenceRef
    metric: MetricName
    value: float | None
    flags: tuple[str, ...] = ()
    encoder_use: dict[str, Any] = {}

    @model_validator(mode="after")
    def _stand_in(self):
        _imported(self.config_hash, self.task_version)
        return self


ResultRecord = Annotated[RunRecord | ScoreRecord, Field(discriminator="kind")]


Value = Annotated[float, Field(allow_inf_nan=False)] | int | NonEmpty


class PredictionRecord(Contract):
    """One line of a run's `predictions.jsonl`: one answer for one target of one atom task. It is the only handoff
    from a run to the scorer (R-77); the agent runner writes these from the agent's submission file."""

    run_id: NonEmpty
    atom: NonEmpty  # the atom task's id
    target: NonEmpty
    value: Value  # a number, or a class label as text; never true or false
    intelligence: IntelligenceRef


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
