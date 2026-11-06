"""Recipes (part 6): S1's ported recipes validate; references across files are checked."""
import shutil
from pathlib import Path

import pytest
import yaml

from medomni.core import contracts as c
from medomni.core import families
from medomni.core.recipes import check_cohort, check_package
from medomni.core.testing import DATASETS

FIXTURES = Path(__file__).parent / "fixtures" / "recipes"
REPO = Path(__file__).resolve().parents[2]


def test_s1_recipes_validate():
    fams = set(families.load_registry(REPO))
    n_cohorts = n_labels = 0
    for d in sorted(FIXTURES.iterdir()):
        labels = c.load(d / "labels.yaml", c.LabelLibrary)
        n_labels += len(labels.root)
        for name, entry in yaml.safe_load((d / "cohorts.yaml").read_text()).items():
            cohort = c.load_data(entry["cohort"], c.Cohort, name)
            assert check_cohort(name, cohort, dataset=d.name, targets=entry["targets"], labels=labels,
                                conditions=None, codes=None, families=fams) == [], name
            n_cohorts += 1
        if (d / "evidence.yaml").exists():
            c.load(d / "evidence.yaml", c.EvidenceRules)
    assert (n_cohorts, n_labels) == (35, 49)


def test_s1_forms_the_contracts_gained():
    mimic = c.load(FIXTURES / "mimic/labels.yaml", c.LabelLibrary).root
    assert mimic["outcome:readmit-30d"].other_visit and mimic["outcome:in-hospital-death"].same_visit
    assert mimic["outcome:los-gt7"].none == "MIMIC//DISCHARGE"
    bdsp = yaml.safe_load((FIXTURES / "bdsp/cohorts.yaml").read_text())
    conv = [q for e in bdsp.values() for q in e["cohort"].get("require", []) if "converts" in q]
    assert len(conv) == 6
    ev = c.load(FIXTURES / "mimic/evidence.yaml", c.EvidenceRules)
    assert ev.tables["labevents"].drop == "guard" and ev.tables["admissions"].blank_in_index_visit == "guard.fields"


@pytest.mark.parametrize("shape", ["dummy-mimic", "dummy-omop", "dummy-bdsp"])
def test_dummy_packages_cross_check(shape):
    assert check_package(DATASETS / shape) == []


def _pkg(tmp_path):
    pkg = tmp_path / "dummy-mimic"
    shutil.copytree(DATASETS / "dummy-mimic", pkg)
    return pkg


def _edit(path, fn):
    data = yaml.safe_load(path.read_text())
    fn(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


TEMPLATE = "tasks/dummy-mimic_aki/template.yaml"
COHORT = "tasks/dummy-mimic_aki/cohorts/n4.yaml"


@pytest.mark.parametrize("file, edit, match", [
    (TEMPLATE, lambda d: d["targets"][0].update(label="dummy-mimic:sepsis"), "label 'sepsis'"),
    (TEMPLATE, lambda d: d["targets"][0].update(label="other-ds:aki"), "names a label of other-ds"),
    ("labels.yaml", lambda d: d["aki"]["guard"].update(codes=["^NOPE//"]), "guard: code '\\^NOPE//'"),
    ("labels.yaml", lambda d: d["aki"].update(exists="^SEPSIS//"), "label aki: code"),
    (COHORT, lambda d: d["require"].append({"has_label": "sepsis"}), "has_label names 'sepsis'"),
    (COHORT, lambda d: d["draw"].update(by=["sepsis"]), "draw.by names 'sepsis'"),
    (COHORT, lambda d: d["require"].append({"condition": "adult"}), "condition 'adult'"),
    (COHORT, lambda d: d["require"].append({"files": ["no-such-family"]}), "unknown family"),
    (COHORT, lambda d: d["require"].append({"any": ["^NOPE//"]}), "matches nothing"),
    ("evidence.yaml", lambda d: d["tables"].update(no_table={"time": "t"}), "table 'no_table'"),
])
def test_references_are_checked(tmp_path, file, edit, match):
    pkg = _pkg(tmp_path)
    _edit(pkg / file, edit)
    problems = check_package(pkg)
    assert any(__import__("re").search(match, p) for p in problems), problems


def test_shared_codes_need_no_listing():
    assert check_cohort("x", c.load_data({"source": "all", "anchor": {"event": "ICU_ADMISSION"},
                                           "require": [{"any": ["^DIAGNOSIS//ICD//(N17|584)"]}],
                                           "draw": {"n": 4, "seed": 7}}, c.Cohort),
                        dataset="d", targets={}, labels=c.load_data({"x": {"exists": "A", "from": "any", "to": "any"}},
                                                                     c.LabelLibrary),
                        conditions=None, codes={"A"}, families=set()) == []


@pytest.mark.parametrize("draw, ok", [({"n": 4, "seed": 7}, True), ({"n": 4, "seed": "2026|ladder", "by": ["a"]}, True),
                                      ({"n": 0, "seed": 7}, False), ({"n": 4}, False), ({"seed": 7}, False)])
def test_draw(draw, ok):
    data = {"source": "all", "anchor": {"event": "ADMISSION"}, "draw": draw}
    if ok:
        c.load_data(data, c.Cohort)
    else:
        with pytest.raises(c.ContractError):
            c.load_data(data, c.Cohort)


def test_label_rules():
    c.load_data({"x": {"none": "A", "from": "anchor", "to": "anchor + 1 days", "same_visit": True}}, c.LabelLibrary)
    with pytest.raises(c.ContractError, match="exclude each other"):
        c.load_data({"x": {"exists": "A", "from": "any", "to": "any", "same_visit": True, "other_visit": True}},
                    c.LabelLibrary)
    with pytest.raises(c.ContractError, match="exactly one"):
        c.load_data({"x": {"exists": "A", "none": "B", "from": "any", "to": "any"}}, c.LabelLibrary)
    c.load_data({"source": "all", "anchor": {"event": "A"}, "require": [{"converts": {"min_families": 3}}],
                 "draw": {"n": 4, "seed": 7}}, c.Cohort)
