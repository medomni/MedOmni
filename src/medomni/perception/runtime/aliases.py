"""What each family accepts: supply labels, label parts, rates, prefixes and colour modes.

They come from Core's families module, the same resolver Core and Bench use (R-120). In an encoder image the
repository's `core/families/` folder is copied in and `MEDOMNI_ROOT` names its parent; in a clone it is found from the
working folder.
"""
import os
from functools import cache
from pathlib import Path

from medomni.core.families import aliases as _core


def _root():
    root = os.environ.get("MEDOMNI_ROOT")
    return Path(root) if root else None


@cache
def _aliases_for(family):
    a = _core.resolve(family, _root())
    return {"labels": dict(a.labels), "components": dict(a.components), "rates": frozenset(a.rates),
            "prefixes": tuple(a.prefixes), "colors": frozenset(a.colors)}


def _normalize_label(value):
    return _core.normalize_label(str(value))


def _resolve_label(family, value):
    """Resolve only prefixes and aliases declared for this family."""
    aliases = _aliases_for(family)
    folded = str(value).strip().casefold()
    prefix_used = False
    for prefix in aliases["prefixes"]:
        if folded.startswith(prefix):
            folded = folded[len(prefix):]
            prefix_used = True
            break
    source = _normalize_label(folded)
    parts = [aliases["components"].get(part, part) for part in source.split("-")]
    component_resolved = "-".join(parts)
    resolved = aliases["labels"].get(component_resolved, component_resolved)
    return resolved, prefix_used or resolved != source
