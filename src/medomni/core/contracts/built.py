"""The built-task contract (R-143): the files any task builder writes and Bench reads (`medomni.core.tasks`).

A builder may write more than these fields (its own counts, its own records); Bench reads only these.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .base import NonEmpty


class _Open(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")


class BuiltTarget(_Open):
    name: NonEmpty
    metric: NonEmpty  # registered in medomni.metrics


class BuiltAtom(_Open):
    atom: NonEmpty  # the atom folder's name
    subject: NonEmpty
    prediction_time: str | None = None


class BuiltContent(_Open):
    """`_content/<task>/content.json`."""

    version: NonEmpty  # the task's version N.X (R-106)
    targets: tuple[BuiltTarget, ...] = Field(min_length=1)
    atoms: tuple[BuiltAtom, ...] = Field(min_length=1)


class BuiltManifest(_Open):
    """`_content/<task>/manifest.json`."""

    config_hash: dict[str, NonEmpty]  # `<arm>` or `<arm>/<variant>` -> cfg1 hash (R-111)
    builder: NonEmpty  # `<name>/<version>` of the builder that wrote the task (R-142)


ANSWERS = ("subject_id", "target", "value", "metric")  # answers.csv's header
ATOM_FILES = ("task.toml", "instruction.md", "tests/expected.json", "tests/format_check.py", "tests/test.sh",
              "environment/docker-compose.yaml", "environment/Dockerfile")  # what the agent runner and the scorer read
GOLD_NAMES = ("answers.csv", "gold.csv", "content.json", "record.json")  # never inside an atom
