"""Contracts: one typed, frozen model per file or message that passes between parts.

`load(path, Model)` reads a file and returns the checked object; code never works with the raw dict. Each model's
JSON Schema is generated into `schemas/` for tools outside Python (`python -m medomni.core.contracts.schemas`).

This module imports pydantic. The command layer imports it only when a contract command runs.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, TypeAdapter

from .base import Contract, ContractError, IntelligenceRef, load, load_data, load_lines, read
from .built import BuiltContent, BuiltManifest
from .dataset import DatasetConfig, DatasetPolicy, Event, EventTable
from .family import AliasFile, FamilyFile
from .perception import ContainerRequest, ContainerResponse, EncodeRequest, Evidence, ModelCard
from .recipe import Cohort, CohortTests, EvidenceRules, LabelLibrary
from .run import AgentConfig, CacheEntry, PredictionRecord, ResultRecord, RunRecord, ScoreRecord, WorkspaceConfig
from .task import BenchmarkCard, TaskProposal, TaskSet, TaskTemplate


@dataclass(frozen=True)
class Schema:
    contract: str  # the contract's name on the Contracts page
    file: str  # schemas/<file>.schema.json
    model: object  # a model class, or a type for TypeAdapter (ResultRecord)


# The 18 contracts, and the schema file of each model in them
SCHEMAS = (
    Schema("family registry", "family", FamilyFile),
    Schema("family registry", "aliases", AliasFile),
    Schema("dataset config", "dataset-config", DatasetConfig),
    Schema("event table", "event-table", EventTable),
    Schema("event table", "event", Event),
    Schema("dataset policy", "dataset-policy", DatasetPolicy),
    Schema("recipe", "recipe", Cohort),
    Schema("recipe", "recipe-tests", CohortTests),
    Schema("recipe", "recipe-labels", LabelLibrary),
    Schema("recipe", "recipe-evidence", EvidenceRules),
    Schema("task template", "task-template", TaskTemplate),
    Schema("benchmark", "benchmark", BenchmarkCard),
    Schema("task set", "task-set", TaskSet),
    Schema("cache entry", "cache-entry", CacheEntry),
    Schema("agent config", "agent-config", AgentConfig),
    Schema("task proposal", "task-proposal", TaskProposal),
    Schema("model card", "model-card", ModelCard),
    Schema("container API", "container-request", ContainerRequest),
    Schema("container API", "container-response", ContainerResponse),
    Schema("gateway API", "gateway-api", EncodeRequest),
    Schema("gateway API", "evidence", Evidence),
    Schema("result record", "result-record", ResultRecord),
    Schema("prediction record", "prediction-record", PredictionRecord),
    Schema("workspace config", "workspace-config", WorkspaceConfig),
    Schema("built task", "built-content", BuiltContent),
    Schema("built task", "built-manifest", BuiltManifest),
)

CONTRACTS = tuple(dict.fromkeys(s.contract for s in SCHEMAS))


def json_schema(model) -> dict:
    if isinstance(model, type) and issubclass(model, BaseModel):
        return model.model_json_schema(by_alias=True)
    return TypeAdapter(model).json_schema(by_alias=True)


__all__ = [
    "AgentConfig", "AliasFile", "BenchmarkCard", "CacheEntry", "Cohort", "CohortTests", "ContainerRequest", "ContainerResponse",
    "Contract", "ContractError", "CONTRACTS", "DatasetConfig", "DatasetPolicy", "EncodeRequest", "Event",
    "EventTable", "Evidence", "EvidenceRules", "FamilyFile", "IntelligenceRef", "LabelLibrary",
    "ModelCard", "PredictionRecord", "ResultRecord", "RunRecord", "SCHEMAS", "ScoreRecord", "TaskProposal",
    "TaskSet", "TaskTemplate", "WorkspaceConfig", "json_schema", "load", "load_data", "load_lines",
    "read",
]
