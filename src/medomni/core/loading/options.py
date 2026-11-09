"""The options of the format readers a dataset config's `read` list names (Datasets reference page).

Part 5's dummy-data generator writes raw folders from these options, and part 6's readers read them, so both follow
one definition. The `csv` reader reads tables; the `tree` reader finds family files by folder pattern.

    read:
    - reader: csv
      options:
        tables:
          admissions:
            file: hosp/admissions.csv
            subject: subject_id
            subject_type: int
            time: admittime
            visit: hadm_id
            events:
            - code: ADMISSION
            - {code: DISCHARGE, time: dischtime}
          labevents:
            file: hosp/labevents.csv
            subject: subject_id
            time: charttime
            events:
            - {code: "LAB//{itemid}", value: valuenum}
    - reader: tree
      options:
        files:
          cxr-radiograph-2d: {pattern: "cxr/{subject}/{record}.png"}
          psg-night: {pattern: "psg/{subject}/{record}.h5", format: h5, families: [eeg-sleep-6ch-200hz-uv, ...]}
"""
from __future__ import annotations

import re
import string
from typing import Literal

from pydantic import Field, model_validator

from medomni.core.contracts.base import Contract, NonEmpty, Slug

PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class TimeFrom(Contract):
    """Rows with no time of their own take it from another table's row with the same key."""

    table: NonEmpty
    key: NonEmpty
    column: NonEmpty


class EventSpec(Contract):
    """One code a table row emits. `{column}` in the code is filled from that column."""

    code: NonEmpty
    value: NonEmpty | None = None  # a numeric column
    text: NonEmpty | None = None  # a text column
    time: NonEmpty | None = None  # a time column other than the table's
    path: NonEmpty | None = None  # FILE//<family> rows: the file or folder, relative to the data root; `{column}` filled
    present: tuple[NonEmpty, ...] = ()  # emit only when these columns are filled
    absent: tuple[NonEmpty, ...] = ()  # emit only when these columns are empty
    equals: dict[NonEmpty, tuple[str, ...]] = {}  # emit only when the column holds one of these values

    def emits(self, row: dict) -> bool:
        return (all(row.get(c, "") for c in self.present) and not any(row.get(c, "") for c in self.absent)
                and all(row.get(c, "") in vals for c, vals in self.equals.items()))

    @property
    def columns(self) -> list[str]:
        return [f for _, f, _, _ in string.Formatter().parse(self.code) if f]

    def pattern(self) -> re.Pattern:
        """A regex that matches the codes this spec can emit, with one group per column."""
        out, pos = "^", 0
        for m in PLACEHOLDER.finditer(self.code):
            out += re.escape(self.code[pos:m.start()]) + f"(?P<{m.group(1)}>.+?)"
            pos = m.end()
        return re.compile(out + re.escape(self.code[pos:]) + "$")


class Clean(Contract):
    """How a column's text is cleaned before codes are filled from it."""

    before: str | None = None  # keep the text before the first occurrence of this, stripped
    remove: str | None = None  # drop each of these characters
    lower: bool = False

    def apply(self, v: str) -> str:
        if self.before:
            v = v.split(self.before, 1)[0].strip()
        if self.remove:
            v = v.translate({ord(c): None for c in self.remove})
        return v.lower() if self.lower else v


class TableSpec(Contract):
    file: NonEmpty  # relative to the data root; a glob (`*`) reads every matching file as one table
    subject: NonEmpty
    subject_type: Literal["str", "int"] = "str"
    time: NonEmpty | None = None  # no time and no time_from: static facts
    time_from: TimeFrom | None = None
    visit: NonEmpty | None = None
    events: tuple[EventSpec, ...] = Field(min_length=1)
    where: dict[NonEmpty, tuple[str, ...]] = {}  # keep only rows whose column holds one of these values
    clean: dict[NonEmpty, Clean] = {}  # column -> how its text is cleaned before codes are filled
    load: bool = True  # false: evidence reads the table, the event table doesn't (a table too large to load)
    missing_time: Literal["keep", "drop"] = "keep"  # drop: a row whose time is empty emits nothing

    def column_names(self) -> list[str]:
        """Every column these options name."""
        need = {self.subject, self.time, self.visit, *self.where, *self.clean}
        if self.time_from:
            need.add(self.time_from.key)
        for e in self.events:
            need |= set(e.columns) | {e.value, e.text, e.time, *e.present, *e.absent, *e.equals}
            if e.path:
                need |= {f for _, f, _, _ in string.Formatter().parse(e.path) if f}
        return sorted(c for c in need if c)

    @model_validator(mode="after")
    def _one_time(self):
        if self.time and self.time_from:
            raise ValueError("a table has a time column or time_from, not both")
        return self


class CsvOptions(Contract):
    tables: dict[NonEmpty, TableSpec] = Field(min_length=1)


class SubjectFrom(Contract):
    """The path's `{subject}` is a key of another table (a folder name), mapped to that table's subject column."""

    table: NonEmpty
    key: NonEmpty


class FileSpec(Contract):
    pattern: NonEmpty  # relative to the data root, with {subject} and {record}
    format: Literal["family", "h5"] = "family"  # h5: one raw night that a converter turns into several families
    families: tuple[Slug, ...] = ()  # for h5; a family-format entry is named by its family
    per_subject: int = Field(default=1, ge=1)
    exclude: tuple[NonEmpty, ...] = ()  # skip a path holding any of these
    subject_from: SubjectFrom | None = None

    @model_validator(mode="after")
    def _placeholders(self):
        if "{subject}" not in self.pattern or "{record}" not in self.pattern:
            raise ValueError("a file pattern holds {subject} and {record}")
        if self.format == "h5" and not self.families:
            raise ValueError("an h5 entry lists the families it carries")
        return self


class TreeOptions(Contract):
    files: dict[NonEmpty, FileSpec] = Field(min_length=1)


class HookOptions(Contract):
    """A package hook (`hooks/<hook>.py`): Python for what no reader option can say. It runs after the other
    readers, sees their rows, and returns more rows (Datasets reference page, Hooks)."""

    hook: Slug
    params: dict = {}


READERS = {"csv": CsvOptions, "tree": TreeOptions, "hook": HookOptions}


def options(reader) -> Contract:
    """A dataset config's reader entry, with its options checked."""
    from medomni.core.contracts import load_data

    try:
        model = READERS[reader.reader]
    except KeyError:
        raise ValueError(f"unknown reader '{reader.reader}' (known: {', '.join(sorted(READERS))})") from None
    return load_data(dict(reader.options), model, f"read: {reader.reader}")
