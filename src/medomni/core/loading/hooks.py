"""Package hooks: Python a dataset package carries for what no reader option can say (Datasets reference page).

A hook is `<package>/hooks/<name>.py`, named in `dataset.yaml` by a `hook` reader:

    read:
    - reader: hook
      options: {hook: ckd, params: {creatinine: [LAB//50912, LAB//52546]}}

Hooks run after the csv and tree readers, in the order listed. The module defines:

| Name | Required | Does |
|---|---|---|
| `derive(rows, raw_root, params)` | yes | Returns new event rows. `rows` are the rows read so far (do not change them); a hook may also read raw files. |
| `inputs(raw_root, params)` | no | The raw files it reads, relative to the data root: `verify` checks they exist and they join the cache key. |
| `dummy(raw_root, subjects, params, rng)` | no | Writes those raw files for a dummy copy. `subjects` maps each subject id to its `t0`. |

Every code a hook emits is listed in `codes.csv` with `source_table` `hook:<name>`, and is checked like any other.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .readers import LoadError

COLUMNS = ("subject_id", "time", "code", "numeric_value", "text_value", "visit_id", "path", "sha256", "native_id")


def file_module(package: Path, rel: str, kind: str = "file"):
    """A Python file of a dataset package, loaded by path: the package is a folder, not an installed module (R-145)."""
    path = Path(package) / rel
    if not path.is_file():
        raise LoadError(f"{kind} {rel}: no {path.relative_to(Path(package).parent)}")
    name = f"medomni_{kind}_{Path(package).name.replace('-', '_')}_{path.stem}"
    mod = sys.modules.get(name)
    if mod is not None and Path(getattr(mod, "__file__", "")) == path:  # one module per file, so its classes are one
        return mod
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def module(package: Path, name: str, derives: bool = True):
    path = Path(package) / "hooks" / f"{name}.py"
    if not path.is_file():
        raise LoadError(f"read: hook {name}: no {path.relative_to(Path(package).parent)}")
    spec = importlib.util.spec_from_file_location(f"medomni_hook_{Path(package).name.replace('-', '_')}_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if derives and not callable(getattr(mod, "derive", None)):
        raise LoadError(f"read: hook {name}: defines no derive(rows, raw_root, params)")
    return mod


def inputs(package: Path, name: str, raw_root: Path, params: dict) -> list[str]:
    mod = module(package, name)
    return list(mod.inputs(Path(raw_root), dict(params))) if hasattr(mod, "inputs") else []


def derive(package: Path, name: str, rows: list[dict], raw_root: Path, params: dict) -> list[dict]:
    """The hook's rows, with every event column present and `_table` naming the hook."""
    mod = module(package, name)
    out = []
    for r in mod.derive(rows, Path(raw_root), dict(params)):
        extra = set(r) - set(COLUMNS)
        if extra or not r.get("subject_id") or not r.get("code"):
            raise LoadError(f"read: hook {name}: a row needs subject_id and code and only event columns "
                            f"(extra: {sorted(extra)})")
        out.append({**{c: None for c in COLUMNS}, **r, "subject_id": str(r["subject_id"]), "_table": f"hook:{name}"})
    return out
