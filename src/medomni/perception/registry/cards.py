"""What an encoder folder must hold before anything serves it: a card that passes Core's model card contract, an id
that matches the folder, a family Core declares, and, for a runnable encoder, a Dockerfile that runs the shared
runtime. The gateway's catalogue serves only folders that pass (R-25)."""
from pathlib import Path

import yaml

from . import ID_RE, encoder_id

RUNTIME_ENTRY = "medomni.perception.runtime.serve"


def load_card(edir):
    return yaml.safe_load((Path(edir) / "card.yaml").read_text(encoding="utf-8"))


def find_todos(node, path="card"):
    if isinstance(node, str) and node.strip().startswith("TODO"):
        return [path]
    if isinstance(node, dict):
        return [t for k, v in node.items() for t in find_todos(v, f"{path}.{k}")]
    if isinstance(node, list):
        return [t for i, v in enumerate(node) for t in find_todos(v, f"{path}[{i}]")]
    return []


def dockerfile_problems(path):
    """What a runnable encoder's Dockerfile lacks: the shared runtime, run as its entry point."""
    text = "\n".join(line for line in Path(path).read_text(encoding="utf-8").splitlines()
                     if not line.lstrip().startswith("#"))
    return [] if RUNTIME_ENTRY in text else [f"does not run the shared runtime ({RUNTIME_ENTRY})"]


def check(edir, families=None):
    """(errors, warnings) for one encoder folder. `families`: the family ids Core declares (read when not given)."""
    from medomni.core.contracts import ContractError, ModelCard, load_data

    edir = Path(edir)
    errs, warns = [], []
    try:
        card = load_card(edir)
    except (OSError, yaml.YAMLError) as exc:
        return [f"card.yaml cannot be read: {exc}"], []
    if not isinstance(card, dict):
        return ["card.yaml is not a mapping"], []
    try:
        load_data(card, ModelCard, "card")
    except ContractError as exc:
        errs += [f"{where}: {msg}" if where else msg for where, msg in exc.problems]

    cid = card.get("id")
    if cid != encoder_id(edir):
        errs.append(f"id '{cid}' != directory identity '{encoder_id(edir)}'")
    if isinstance(cid, str) and ID_RE.match(cid):
        family = cid.split("__", 1)[0]
        if families is None:
            from medomni.core import families as core_families

            families = set(core_families.load_registry())
        if family not in families:
            errs.append(f"family '{family}' is not declared in core/families/")

    for block in card.get("outputs") or []:
        if isinstance(block, dict) and block.get("kind") in ("labels", "events") and not block.get("labels"):
            warns.append(f"outputs block '{block.get('kind')}' declares no label vocabulary; its labels are not checked")

    has_adapter = (edir / "adapter.py").is_file()
    if has_adapter and not (edir / "Dockerfile").is_file():
        errs.append("adapter.py present but no Dockerfile")
    elif has_adapter:
        errs += [f"Dockerfile {p}" for p in dockerfile_problems(edir / "Dockerfile")]
    if has_adapter and not (edir / "testdata" / "expected.json").is_file():
        warns.append("adapter.py present but no testdata/expected.json: untested")
    if not has_adapter:
        warns.append("card only, no adapter yet")
    todos = find_todos(card)
    if todos:
        warns.append(f"{len(todos)} TODO field(s): {', '.join(todos)}")
    return errs, warns
