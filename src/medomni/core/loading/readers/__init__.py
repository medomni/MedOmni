"""Format readers: each turns its part of a raw folder into event rows (dicts with the event table's columns).

`csv` reads tables by the dataset config's code templates; `tree` finds family files by folder pattern and reads
each file's header for its time. pandas and pyarrow are imported inside the readers, never at import time.
"""
from __future__ import annotations


class LoadError(ValueError):
    """Loading stopped; the message names the step and what failed."""
