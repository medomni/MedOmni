"""Every label's guard equals what v0.2's one leakage truth bans (R-47). Reads v0.2's source until part 8; no data."""
import ast
import importlib.util
import sys
import types
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
V = REPO / "data_task/taskbuilder"


@pytest.fixture(scope="module")
def banned():
    if not V.is_dir():
        pytest.skip("v0.2's leakage registry is gone")
    named = next(ast.literal_eval(n.value) for n in ast.parse((V / "registry/derivations/__init__.py").read_text()).body
                 if isinstance(n, (ast.Assign, ast.AnnAssign))
                 and getattr((n.targets[0] if isinstance(n, ast.Assign) else n.target), "id", "") == "NAMED")
    reg, der = types.ModuleType("registry"), types.ModuleType("registry.derivations")
    der.NAMED, reg.derivations = named, der
    saved = {k: sys.modules.get(k) for k in ("registry", "registry.derivations")}
    sys.modules.update({"registry": reg, "registry.derivations": der})
    spec = importlib.util.spec_from_file_location("leak", V / "registry/leakage.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    yield mod.banned
    for k, v in saved.items():
        sys.modules.pop(k, None) if v is None else sys.modules.__setitem__(k, v)


@pytest.mark.parametrize("dataset", ["mimic-iv", "aireadi", "bdsp"])
def test_guards_match_v02(dataset, banned):
    lib = yaml.safe_load((REPO / "studio/datasets" / dataset / "labels.yaml").read_text())
    for name, rule in lib.items():
        if name == "derived:cxr-before-anchor":
            continue  # balance only: never a target
        b, g = banned(name), rule.get("guard", {})
        fields = set(b.get("admission_fields", ())) | set(b.get("demo_columns", ()))
        assert set(g.get("fields", ())) == fields, name
        omop = "^(OMOP|CONDITION|PROCEDURE)//"
        codes = {f"{omop}{c}$" for c in b.get("omop_codes", ())} | {f"LAB//{i}" for i in b.get("lab_itemids", ())}
        codes |= {f"{omop}{p}" for p in b.get("omop_prefix_codes", ())}
        have = set(g.get("codes", ()))
        assert codes <= have, name
        pats = have - codes
        assert (len(pats) == 1 and all(p in next(iter(pats)) for p in b["icd_prefixes"])) if b.get("icd_prefixes") else not pats, name
