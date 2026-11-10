"""`medomni bench data connect`: record where your copy of a dataset is (R-144). Checking a copy against its dataset
package is Studio's (`medomni studio data check`), since packages are the v1 builder's input.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from medomni.core import workspace


def connect(dataset: str, path: str, stream=None) -> int:
    """Record the copy's folder in the workspace config, keeping the rest of the file as written."""
    stream = stream or sys.stdout
    raw = Path(path).expanduser()
    if not raw.is_absolute() or not raw.is_dir():
        print(f"{path} is not an absolute path to a folder", file=stream)
        return 1
    cfg = workspace.config_path()
    if not cfg.is_file():
        print(f"no workspace config at {cfg} (see Get started)", file=stream)
        return 1
    line = f"  {dataset}: {{path: {raw}}}\n"
    lines = cfg.read_text(encoding="utf-8").splitlines(keepends=True)
    entry = re.compile(rf"^  {re.escape(dataset)}:")
    start = next((i for i, x in enumerate(lines) if re.match(r"^datasets:\s*(\{\s*\})?\s*$", x)), None)
    if start is None:
        lines = ["datasets:\n", line, *lines]
    else:
        lines[start] = "datasets:\n"
        at = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("  ") is False or entry.match(lines[i])),
                  len(lines))
        if at < len(lines) and entry.match(lines[at]):
            lines[at] = line
        else:
            lines.insert(start + 1, line)
    cfg.write_text("".join(lines), encoding="utf-8")
    workspace.load()  # refuse now, not later, if the edit broke the file
    print(f"{dataset}: {raw}", file=stream)
    return 0
