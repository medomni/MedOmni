"""Comparing a timestamp with a prediction time, for checks over built output: datetimes, dates, or seconds from a start."""
from __future__ import annotations

import datetime as dt

F = "%Y-%m-%d %H:%M:%S"


def parse(s) -> dt.datetime | None:
    if not s:
        return None
    s = str(s).strip().replace("T", " ")
    try:
        return dt.datetime.strptime(s[:19], F) if len(s) > 10 else \
            dt.datetime.strptime(s[:10], "%Y-%m-%d") + dt.timedelta(hours=23, minutes=59, seconds=59)
    except ValueError:
        return None


def _is_number(s) -> bool:
    try:
        float(s)
    except (TypeError, ValueError):
        return False
    return True


def before_or_at(ts, b: str | None) -> bool:
    """A timestamp coarser than the boundary is compared conservatively: a date counts as the end of that day."""
    if not b or ts in (None, ""):
        return True
    if _is_number(b):  # a dataset timed in seconds from the start
        return not _is_number(ts) or float(ts) <= float(b)
    t, limit = parse(ts), parse(b)
    return t is None or t <= limit
