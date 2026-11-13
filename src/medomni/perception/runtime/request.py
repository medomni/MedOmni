"""Request checks: the body against the card, and the path confined under the data root."""
import os
from pathlib import Path

from .errors import BadRequest


# ---------------- request ----------------

def parse_request(body, card):
    """Validate a request body against the card. Returns (family, rel_path, options)."""
    if not isinstance(body, dict):
        raise BadRequest("body must be a JSON object")
    for key in body:
        if key not in ("family", "path", "options"):
            raise BadRequest(f"unknown field '{key}'")
    family = body.get("family")
    rel = body.get("path")
    if not isinstance(family, str) or not family:
        raise BadRequest("'family' is required and must be a string")
    if not isinstance(rel, str) or not rel:
        raise BadRequest("'path' is required and must be a string")
    if family != card["family"]:
        raise BadRequest(
            f"family mismatch: caller asserted '{family}', this encoder reads '{card['family']}'")
    options = body.get("options") or {}
    if not isinstance(options, dict):
        raise BadRequest("'options' must be an object")
    return family, rel, options


def resolve_path(rel, data_root=None):
    """Resolve rel under $DATA_ROOT and confine it there.

    Symbolic links resolve before the comparison, so a link pointing out of the
    root is rejected like any other escape.
    """
    root = Path(data_root or os.environ.get("DATA_ROOT", "/data")).resolve()
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        raise BadRequest(f"path escapes DATA_ROOT: '{rel}'")
    if not target.exists():
        raise BadRequest(f"no such file: '{rel}'")
    if not target.is_file():
        # '' and '.' resolve to the root itself, and a directory is not an input;
        # answering 400 here keeps the reader from failing on an open() it cannot do.
        raise BadRequest(f"not a file: '{rel}'")
    return target
