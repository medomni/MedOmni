"""What one audit looks at: the datasets in the workspace, the families and encoders in the repository, the built
pairs (every built one, or one set's), and the runs in the results file."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from .. import common
from .engine import Masker


@dataclass
class Scope:
    ws: object
    pairs: list[str]
    samples: Path | None = None  # a folder of family samples, one sub-folder per family
    mask: Masker = field(default_factory=Masker)

    def __post_init__(self):
        # every atom and subject is registered before any check writes a detail, as v0.2's scope did
        for pair in self.pairs:
            meta = common.content(self.ws, pair)
            for a in (meta or {}).get("atoms", []):
                self.mask.register(a["atom"], str(a["subject"]))

    @cached_property
    def datasets(self) -> list[str]:
        return sorted(self.ws.datasets)

    @cached_property
    def families(self) -> dict:
        from medomni.core import families

        return families.load_registry()

    @cached_property
    def encoders(self) -> list[Path]:
        return common.encoder_dirs()

    @cached_property
    def run_records(self) -> tuple[list, list]:
        return common.results(self.ws)
