"""The four built-in arms' run side (R-84, R-85, R-143 c): what a run attaches. An arm is one name in `medomni.arms`;
what it hides or shows in a built task is each builder's own (`medomni.arm_builds`), and a builder refuses an arm it has
no build side for.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Arm:
    name: str
    description: str
    perception: str = "on"  # on, off, forced: whether the run attaches the perception service, and must call it
    max_calls: int | None = 300  # the service's call budget; None: no service


encoders = Arm("encoders", "The agent has the record and the perception service's encoders.")
no_perception = Arm("no-perception", "The agent has the record and no encoders.", perception="off", max_calls=None)
encoders_required = Arm("encoders-required", "As encoders, with one required encoder call and a larger call budget.",
                        perception="forced", max_calls=1000)
modality_ladder = Arm("modality-ladder", "Six cumulative levels of the record, from demographics to everything.")
