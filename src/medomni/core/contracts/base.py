"""What every contract shares: the base model, the error, and reading a file into a checked object."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints, ValidationError


class Contract(BaseModel):
    """A contract model: no unknown fields, and the object cannot be changed after it is read."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, populate_by_name=True)


M = TypeVar("M", bound=BaseModel)


class ContractError(ValueError):
    """A file does not follow its contract. Names the file and every field that is missing or wrong."""

    def __init__(self, source: str, problems: list[tuple[str, str]]):
        self.source = source
        self.problems = problems
        super().__init__("\n".join(f"{source}: {field or '<root>'}: {reason}" for field, reason in problems))


def _jsonable(o: Any):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"{type(o).__name__} is not a contract value")


def load_data(data: Any, model: type[M] | Any, source: str = "<data>") -> M:
    """Check parsed data against a model.

    The data goes through JSON first, so YAML and JSON files are checked the same way: lists become tuples,
    dates become ISO strings, and strict mode refuses "1" for a number.
    """
    try:
        text = json.dumps(data, default=_jsonable)
        if isinstance(model, type) and issubclass(model, BaseModel):
            return model.model_validate_json(text, strict=True)
        from pydantic import TypeAdapter  # a union such as ResultRecord

        return TypeAdapter(model).validate_json(text, strict=True)
    except ValidationError as e:
        raise ContractError(source, [(".".join(str(p) for p in err["loc"]), err["msg"]) for err in e.errors()]) from None
    except TypeError as e:
        raise ContractError(source, [("", str(e))]) from None


def read(path: Path) -> Any:
    """Parse a YAML or JSON file. pyyaml is imported here, not at module import."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    import yaml

    return yaml.safe_load(text)


def load(path: Path, model: type[M] | Any) -> M:
    """Read a file and check it against its contract model."""
    path = Path(path)
    try:
        data = read(path)
    except Exception as e:  # unreadable or malformed file
        raise ContractError(str(path), [("", f"cannot parse: {type(e).__name__}: {e}")]) from None
    return load_data(data, model, str(path))


def load_lines(path: Path, model: type[M]) -> list[M]:
    """Read a JSON lines file (such as a run's predictions.jsonl) and check every line against its model."""
    path = Path(path)
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except ValueError as e:
            raise ContractError(f"{path}:{n}", [("", f"cannot parse: {e}")]) from None
        out.append(load_data(data, model, f"{path}:{n}"))
    return out


# Shared field types
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Fingerprint = Annotated[str, StringConstraints(pattern=r"^fp1:[0-9a-f]{64}$")]
EnvRef = Annotated[str, StringConstraints(pattern=r"^\$\{[A-Z][A-Z0-9_]*\}$")]
NonEmpty = Annotated[str, StringConstraints(min_length=1)]


def _metric(v: str) -> str:
    from medomni.core.plugins import metric_names

    known = metric_names()
    if v not in known:
        raise ValueError(f"unknown metric '{v}' (registered in medomni.metrics: {', '.join(sorted(known)) or 'none'})")
    return v


# A metric name, checked against the `medomni.metrics` entry points (R-77)
MetricName = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]*$"), AfterValidator(_metric)]

# The kinds of intelligence MedOmni evaluates (R-76): `agent` in v0.3; `llm` and `model` are added later
IntelligenceKind = Literal["agent"]


class IntelligenceRef(Contract):
    """The intelligence a run, score or prediction belongs to: its kind and the name of its config."""

    kind: IntelligenceKind
    name: Slug
