"""The v1 builder's own contracts (R-142, R-147): its recipe, its task template, and the stricter `dataset.yaml`
model whose `definitions` are recipe requirements. Core keeps the dataset config the loader reads."""
from __future__ import annotations

from medomni.core.contracts import DatasetConfig

from .recipe import Cohort, CohortTests, EvidenceRules, LabelLibrary, Requirement
from .template import Pair, TaskTemplate, TemplateId


class V1DatasetConfig(DatasetConfig):
    """`dataset.yaml` as the v1 builder reads it: each definition is a recipe requirement (R-89, R-147)."""

    definitions: dict[str, Requirement] = {}


__all__ = ["Cohort", "CohortTests", "EvidenceRules", "LabelLibrary", "Pair", "Requirement", "TaskTemplate", "TemplateId",
           "V1DatasetConfig"]
