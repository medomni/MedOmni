"""One seeded model per dummy subject (part 5b): the planted facts every one of the subject's files follows.

A subject has a resting heart rate and breathing rate, a sleep-stage sequence in 30 s epochs, an SpO2 baseline with
planted desaturations, body positions and planted leg movements. Heart rate rises in wake and REM and falls in N3, as
in a real night. Every value is drawn from the seed within published adult ranges; nothing is fitted to patient data.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from . import rng

EPOCH = 30.0  # seconds, the AASM scoring epoch
STAGES = ("W", "N1", "N2", "N3", "REM")
# One compressed sleep cycle; a subject's night is this cycle from a seeded starting point, so a 5-minute file
# still holds every stage
CYCLE = ("W", "N1", "N2", "N2", "N3", "N3", "N2", "REM", "REM", "N2")
HR_BY_STAGE = {"W": 1.08, "N1": 1.02, "N2": 0.97, "N3": 0.93, "REM": 1.05}  # times the resting rate
POSITIONS = 5  # position codes 0..4


@dataclass(frozen=True)
class Subject:
    seed: int
    key: str
    hr: float  # resting heart rate, bpm (adults 60-100)
    br: float  # breathing rate, breaths per minute (adults 12-20)
    spo2: float  # SpO2 baseline, % (95-99)
    sbp: float  # systolic / diastolic pressure, mmHg
    dbp: float
    start_epoch: int  # where in CYCLE the file starts
    desaturations: tuple[float, ...]  # start times (s) of planted dips of DESAT_DEPTH %
    leg_movements: tuple[float, ...]  # start times (s) of planted limb EMG bursts
    position_changes: tuple[float, ...]  # times (s) the body position code changes

    DESAT_DEPTH = 5.0
    DESAT_SECONDS = 40.0

    def stage(self, t: float) -> str:
        return CYCLE[(self.start_epoch + int(t // EPOCH)) % len(CYCLE)]

    def stages(self, seconds: float) -> list[str]:
        return [self.stage(i * EPOCH) for i in range(int(seconds // EPOCH))]

    def hr_at(self, t: np.ndarray) -> np.ndarray:
        """Heart rate over time: the stage's level, smoothed over a few seconds so beats don't jump."""
        steps = np.array([self.hr * HR_BY_STAGE[self.stage(x)] for x in t])
        k = max(1, int(len(t) / max(t[-1], 1) * 5)) if len(t) > 1 else 1
        return np.convolve(steps, np.ones(k) / k, mode="same") if len(t) > k else steps

    def beats(self, seconds: float) -> np.ndarray:
        """R-peak times (s) for `seconds`, from the heart-rate trajectory."""
        t, out = 0.0, []
        while t < seconds:
            out.append(t)
            t += 60.0 / float(self.hr_at(np.array([t]))[0])
        return np.array(out) + 0.3

    def spo2_at(self, t: np.ndarray) -> np.ndarray:
        x = np.full(len(t), self.spo2, dtype=float)
        for d in self.desaturations:
            down = (t >= d) & (t < d + self.DESAT_SECONDS)
            phase = (t[down] - d) / self.DESAT_SECONDS
            x[down] -= self.DESAT_DEPTH * np.sin(np.pi * phase)  # fall, then recover
        return x

    def position_at(self, t: np.ndarray) -> np.ndarray:
        g = rng(self.seed, self.key, "positions")
        codes = g.integers(0, POSITIONS, size=len(self.position_changes) + 1)
        return codes[np.searchsorted(np.array(self.position_changes), t, side="right")]


@lru_cache(maxsize=256)
def subject(seed: int, key: str, seconds: float = 600.0) -> Subject:
    """The model of one dummy subject. `key` is the subject id, so all of a subject's files agree."""
    g = rng(seed, key, "subject")
    # two dips, each wholly inside the first five minutes, so a 5-minute file holds both in full
    desat = tuple(sorted(float(x) for x in g.uniform(10, 300 - Subject.DESAT_SECONDS - 10, size=2)))
    # keep dips apart so each is counted once
    kept = []
    for d in desat:
        if not kept or d - kept[-1] > Subject.DESAT_SECONDS + 20:
            kept.append(d)
    return Subject(seed=seed, key=key, hr=float(g.uniform(60, 80)), br=float(g.uniform(12, 18)),
                   spo2=float(g.uniform(95, 98)), sbp=float(g.uniform(105, 125)), dbp=float(g.uniform(65, 80)),
                   start_epoch=int(g.integers(0, len(CYCLE))), desaturations=tuple(kept),
                   leg_movements=tuple(sorted(float(x) for x in g.uniform(5, seconds - 5, size=int(seconds // 60)))),
                   position_changes=tuple(sorted(float(x) for x in g.uniform(30, seconds, size=2))))
