"""One JSON Schema per contract model, generated from the models. Regenerate with:

    python -m medomni.core.contracts.schemas
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent


def render() -> dict[str, str]:
    """{file name: schema text} for every contract model."""
    from medomni.core.contracts import SCHEMAS, json_schema

    out = {}
    for s in SCHEMAS:
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{s.file}.schema.json",
                  "x-contract": s.contract} | json_schema(s.model)
        out[f"{s.file}.schema.json"] = json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    return out


def write() -> list[Path]:
    written = []
    for name, text in render().items():
        p = HERE / name
        p.write_text(text, encoding="utf-8")
        written.append(p)
    return written
