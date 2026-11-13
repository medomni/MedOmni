"""Studio's contracts and their JSON Schemas (R-147), written beside this file. Regenerate with:

    python -m medomni.studio.schemas
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent


def schemas():
    from medomni.core.contracts import Schema
    from medomni.studio.build.contracts import Cohort, CohortTests, EvidenceRules, LabelLibrary, TaskTemplate, V1DatasetConfig
    from medomni.studio.propose.contracts import TaskProposal

    return (
        Schema("dataset config", "v1-dataset-config", V1DatasetConfig),
        Schema("recipe", "recipe", Cohort),
        Schema("recipe", "recipe-tests", CohortTests),
        Schema("recipe", "recipe-labels", LabelLibrary),
        Schema("recipe", "recipe-evidence", EvidenceRules),
        Schema("task template", "task-template", TaskTemplate),
        Schema("task proposal", "task-proposal", TaskProposal),
    )


def render() -> dict[str, str]:
    from medomni.core.contracts.schemas import render as core_render

    return core_render(schemas())


def write() -> list[Path]:
    from medomni.core.contracts.schemas import write as core_write

    return core_write(schemas(), HERE)
