"""The encoder adapter interface (R-117): the one file each encoder folder writes.

An adapter is a module with

- `FAMILY`: the family it reads, which must equal its card's `family`;
- `load()` (optional): load the model once, at start; the result reaches `encode` as `options["_model"]`;
- `encode(sample, options)`: a decoded sample in, a list of output blocks out (`labels`, `events`, `text`,
  `embedding` from this package). It raises `Degraded` for input it cannot use, which the caller sees as
  `healthy: false`, and `BadRequest` for options it refuses.

Everything else (request checks, decoding, the response, the server, assets) is the runtime's.
"""
import importlib.util
import os
from pathlib import Path
from typing import Any, Protocol

import yaml

APP = Path(os.environ.get("APP_DIR", "/app"))


class Adapter(Protocol):
    FAMILY: str

    def encode(self, sample: dict, options: dict) -> list[dict[str, Any]]: ...


def load_card(path=None) -> dict:
    """The encoder's card, checked against Core's model card contract; returned as written."""
    from medomni.core.contracts import ModelCard, load_data

    p = Path(path or os.environ.get("CARD_PATH", APP / "card.yaml"))
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    load_data(data, ModelCard, str(p))
    return data


def load_adapter(path=None):
    target = Path(path or os.environ.get("ADAPTER_PATH", APP / "adapter.py"))
    spec = importlib.util.spec_from_file_location(f"adapter_{target.parent.name}", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_adapter(card, adapter):
    """Stop before inference when an adapter and its card name different families, or the adapter has no encode."""
    family = getattr(adapter, "FAMILY", None)
    if family != card["family"]:
        raise RuntimeError(f"adapter reads '{family}' but card declares '{card['family']}'")
    if not callable(getattr(adapter, "encode", None)):
        raise RuntimeError("adapter has no encode(sample, options)")
