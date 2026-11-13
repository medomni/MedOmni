"""`medomni studio diagrams <description>`: the architecture diagrams, as SVG files that also open in draw.io."""
from __future__ import annotations

from pathlib import Path

from ..tools import Report, Result, ToolError


class Diagrams(Report):
    name = "diagrams"
    summary = "draw the architecture diagrams from one description"
    target = "description"
    target_help = "the YAML description, such as docs/assets/diagrams.yaml"

    def options(self, p) -> None:
        pass  # --out names the folder for the SVG files

    def make(self, target, a, ctx) -> Result:
        import yaml

        from .diagrams import Diagram

        path = Path(target)
        if not path.is_file():
            raise ToolError(f"no such description: {path}")
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        files = {f"{name}.drawio.svg": Diagram(d, spec["parts"]).svg() for name, d in spec["diagrams"].items()}
        return Result(f"{len(files)} diagram(s)", files)
