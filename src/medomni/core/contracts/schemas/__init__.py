"""One JSON Schema per contract model, generated from the models. Regenerate with:

    python -m medomni.core.contracts.schemas

A project with its own contracts writes its schemas the same way, from its own list (Studio's: R-147).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent


def render(schemas=None) -> dict[str, str]:
    """{file name: schema text} for every model in `schemas` (Core's own when omitted)."""
    from medomni.core.contracts import SCHEMAS, json_schema

    out = {}
    for s in SCHEMAS if schemas is None else schemas:
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{s.file}.schema.json",
                  "x-contract": s.contract} | json_schema(s.model)
        out[f"{s.file}.schema.json"] = json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    return out


def write(schemas=None, folder: Path = HERE) -> list[Path]:
    written = []
    for name, text in render(schemas).items():
        p = Path(folder) / name
        p.write_text(text, encoding="utf-8")
        written.append(p)
    return written
