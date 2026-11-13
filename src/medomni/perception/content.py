"""Perception's content kinds (R-145): encoder folders and their model cards."""
from medomni.core.contracts import ModelCard
from medomni.core.plugins import Files, Kind

CONTENT = (
    Kind("encoders", "perception/encoders/*/*/card.yaml", 1, name_parts=2),
    Files("model card", "cards", "perception/encoders/*/*/card.yaml", ModelCard),  # the repository's since Stage 3 part 1 (R-66)
)
