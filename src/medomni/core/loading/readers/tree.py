"""The `tree` reader: family files found by folder pattern, one `FILE//<family>` row per file (an h5 night that
several families come from gives one row per family). Times and native ids come from each file's header."""
from __future__ import annotations

import re
from pathlib import Path

from .headers import file_hash, start


def _regex(pattern: str) -> re.Pattern:
    out, pos = "^", 0
    for m in re.finditer(r"\{(subject|record)\}|\*", pattern):
        out += re.escape(pattern[pos:m.start()])
        out += f"(?P<{m.group(1)}>[^/]+)" if m.group(1) else "[^/]*"
        pos = m.end()
    return re.compile(out + re.escape(pattern[pos:]) + "$")


def read(options, root: Path, *, families: set[str] | None = None, stats: dict | None = None) -> list[dict]:
    out = []
    for entry, spec in options.files.items():
        fams = list(spec.families) if spec.format == "h5" else [entry]
        if families is not None and not set(fams) & families:
            continue
        rx = _regex(spec.pattern)
        glob = re.sub(r"\{(subject|record)\}", "*", spec.pattern)
        found = 0
        for p in sorted(root.glob(glob)):
            rel = p.relative_to(root).as_posix()
            m = rx.match(rel)
            if not m or not p.is_file():
                continue
            found += 1
            t, native = start(p)
            h = file_hash(p)
            for f in fams:
                if families is None or f in families:
                    out.append({"subject_id": m.group("subject"), "time": t.isoformat() if t else None,
                                "code": f"FILE//{f}", "numeric_value": None, "text_value": None, "visit_id": None,
                                "path": rel, "sha256": h, "native_id": native, "_table": None})
        if stats is not None:
            stats[entry] = found
    return out
