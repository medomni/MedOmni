"""v0.2 model cards -> v0.3 model cards, for the 44 encoders v0.3.0 ships (R-63).

- `authors` is filled from git history: everyone who authored a commit touching the encoder's folder, in order of
  their first commit there (R-62). Names only until the canonical-email list exists; maintainers correct it and
  add GitHub handles before release.

The converted cards are committed in Stage 3, when Perception moves (R-66). In Stage 2 they are only checked.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ENCODERS = "perception/encoders"
SHIPPED_LIST = "docs/reference/encoders.md"


def shipped(repo: Path) -> list[str]:
    """The encoder ids the Encoders reference page lists under 'Encoders in v0.3.0'."""
    text = (Path(repo) / SHIPPED_LIST).read_text(encoding="utf-8")
    section = text.split("## Encoders in v0.3.0", 1)[1].split("\n## ", 1)[0]
    return sorted(set(re.findall(r"`([a-z0-9-]+__[a-z0-9-]+)`", section)))


def git_authors(repo: Path, rel: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "log", "--reverse", "--format=%aN", "--", rel],
                         capture_output=True, text=True, check=True).stdout.split("\n")
    return list(dict.fromkeys(n.strip() for n in out if n.strip()))


def convert(repo: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    repo = Path(repo)
    outputs, notes = {}, {}
    for eid in shipped(repo):
        family, name = eid.split("__", 1)
        rel = f"{ENCODERS}/{family}/{name}"
        card = yaml.safe_load((repo / rel / "card.yaml").read_text(encoding="utf-8"))
        authors = git_authors(repo, rel)
        if not authors:
            raise ValueError(f"{eid}: no git history for {rel}")
        out = {}
        for k, v in card.items():
            out[k] = v
            if k == "summary":
                out["authors"] = [{"name": a} for a in authors]
        outputs[f"{rel}/card.yaml"] = out
        notes[eid] = {"authors": len(authors)}
    return outputs, notes


def responses(repo: Path) -> dict[str, list[dict]]:
    """The container responses in each shipped encoder's testdata/expected.json, by encoder id."""
    import json

    found = {}
    for eid in shipped(repo):
        family, name = eid.split("__", 1)
        p = Path(repo) / ENCODERS / family / name / "testdata" / "expected.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        found[eid] = list(data.values()) if isinstance(data, dict) else list(data)
    return found
