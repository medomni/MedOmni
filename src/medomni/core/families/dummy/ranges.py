"""Published adult reference ranges for dummy table values (part 5b). Never fitted to a dataset.

A value is matched to a range by the words of its code's description in `codes.csv` (or the column name of a family
table), so a new dataset package gets plausible values without a change here. Normal values fall inside the range;
only planted label events fall outside it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import START


@dataclass(frozen=True)
class Range:
    words: str  # a regex over the description, case-insensitive
    low: float
    high: float
    unit: str
    source: str
    integer: bool = False


HARRISON = "Harrison's Principles of Internal Medicine, 21st ed., appendix: reference values for laboratory tests"
RANGES = (
    Range(r"creatinine", 0.6, 1.2, "mg/dL", HARRISON),
    Range(r"potassium", 3.5, 5.0, "mmol/L", HARRISON),
    Range(r"ha?emoglobin(?!\s*a1c)", 12.0, 17.0, "g/dL", HARRISON),
    Range(r"hba1c|ha?emoglobin\s*a1c", 4.0, 5.6, "%", "ADA Standards of Care in Diabetes 2024, section 2 (normal < 5.7 %)"),
    Range(r"glucose", 70.0, 140.0, "mg/dL", "ADA Standards of Care in Diabetes 2024, section 2 (fasting 70-99; < 140 after meals)"),
    Range(r"heart[ _-]?rate|pulse", 60.0, 100.0, "bpm", "American Heart Association: normal resting heart rate 60-100 bpm"),
    Range(r"resp(iratory)?[ _-]?rate|breathing rate", 12.0, 20.0, "breaths/min", "adult resting respiratory rate 12-20 per minute (Harrison's, physical examination)"),
    Range(r"spo2|oxygen saturation", 95.0, 99.0, "%", "WHO Pulse Oximetry Training Manual (2011): normal SpO2 95-100 %"),
    Range(r"systolic|\bsbp\b", 100.0, 119.0, "mmHg", "2017 ACC/AHA blood pressure guideline: normal < 120 mmHg"),
    Range(r"diastolic|\bdbp\b", 60.0, 79.0, "mmHg", "2017 ACC/AHA blood pressure guideline: normal < 80 mmHg"),
    Range(r"temperature", 36.1, 37.2, "C", HARRISON),
    Range(r"body mass index|\bbmi\b", 18.5, 24.9, "kg/m2", "WHO body mass index classification: normal 18.5-24.9"),
    Range(r"apnea-hypopnea|\bahi\b", 0.0, 4.9, "events/h", "AASM ICSD-3: AHI below 5 is normal"),
    Range(r"\bage\b", 18, 90, "years", "adult cohort ages", integer=True),
    Range(r"year of birth", START.year - 90, START.year - 18, "year", "ages 18-90 at the invented study year", integer=True),
)


def lookup(text: str) -> Range | None:
    return next((r for r in RANGES if re.search(r.words, text or "", re.IGNORECASE)), None)


def value(r: Range, g) -> float:
    v = float(g.uniform(r.low, r.high))
    return float(int(round(v))) if r.integer else round(v, 2)
