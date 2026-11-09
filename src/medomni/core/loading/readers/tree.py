"""The `tree` reader: family files found by folder pattern, one `FILE//<family>` row per file (an h5 night that
several families come from gives one row per family). Times and native ids come from each file's header."""
from __future__ import annotations

import re
from pathlib import Path

from .headers import start


def _regex(pattern: str) -> re.Pattern:
    out, pos = "^", 0
    for m in re.finditer(r"\{(subject|record)\}|\*", pattern):
        out += re.escape(pattern[pos:m.start()])
        out += f"(?P<{m.group(1)}>[^/]+)" if m.group(1) else "[^/]*"
        pos = m.end()
    return re.compile(out + re.escape(pattern[pos:]) + "$")


def matches(spec, root: Path):
    """(path, relative path, path subject) for every file the entry's pattern finds, less its `exclude`. Dotfiles
    and empty files are never data (partial downloads such as `.azDownload-*` shadow their finished twins)."""
    rx = _regex(spec.pattern)
    glob = re.sub(r"\{(subject|record)\}", "*", spec.pattern)
    for p in sorted(root.glob(glob)):
        rel = p.relative_to(root).as_posix()
        m = rx.match(rel)
        if m and p.is_file() and not p.name.startswith(".") and p.stat().st_size > 0 \
                and not any(x in rel for x in spec.exclude):
            yield p, rel, m.group("subject")


def read(options, root: Path, *, families: set[str] | None = None, stats: dict | None = None,
         subject_maps: dict | None = None) -> list[dict]:
    """`subject_maps[entry]` maps a path's {subject} to a subject id (an entry's `subject_from`); a path whose key is
    not in the map is skipped."""
    out = []
    for entry, spec in options.files.items():
        fams = list(spec.families) if spec.format == "h5" else [entry]
        if families is not None and not set(fams) & families:
            continue
        smap = (subject_maps or {}).get(entry)
        found = 0
        for p, rel, key in matches(spec, root):
            subject = smap.get(key) if smap is not None else key
            if subject is None:
                continue
            found += 1
            t, native = start(p)
            for f in fams:
                if families is None or f in families:
                    out.append({"subject_id": subject, "time": t.isoformat() if t else None,
                                "code": f"FILE//{f}", "numeric_value": None, "text_value": None, "visit_id": None,
                                "path": rel, "sha256": None, "native_id": native, "_table": None})
        if stats is not None:
            stats[entry] = found
    return out
