"""The template and cohort converter (R-68): every converted file validates, matches the committed tree and v0.2's
scored targets, and a second run changes nothing. Reads only this repository's v0.2 specs and fixtures."""
from pathlib import Path

import pytest

from medomni.core import contracts as c
from medomni.studio.build import contracts as v1
from tests.repro import migrate as convert
from tests.repro.migrate import templates

SCORED = {  # v0.2's n20 trees: template -> {target: metric} (atomtasks/_parents/*__n20/parent.json)
    'aireadi_cancer-history-metabolic': {'cancer_history': 'auc'},
    'aireadi_cataract-ocular': {'cataract_history': 'auc'},
    'aireadi_cognitive-function-retinal': {'moca_lt_26': 'auc'},
    'aireadi_cognitive-score-metabolic': {'moca_lt_26': 'auc', 'moca_orientation': 'mae', 'moca_abstraction': 'mae', 'moca_mis': 'mae'},
    'aireadi_crp-wcc-lifestyle': {'hs_crp_ge_3': 'auc', 'wbc_value': 'mae'},
    'aireadi_crp-white-cell-count-2': {'hs_crp_ge_3': 'auc', 'wbc_value': 'mae'},
    'aireadi_crp-white-cell-count': {'hs_crp_ge_3': 'auc', 'wbc_value': 'mae'},
    'aireadi_depression-lifestyle': {'cesd10_ge_10': 'auc'},
    'aireadi_diabetes-diagnosis-biopsycho': {'diabetes_status': 'qwk'},
    'aireadi_diabetes-retinal': {'diabetes_status': 'qwk'},
    'aireadi_dpn-neuropathy-metabolic': {'foot_sensation_impaired_right': 'auc', 'foot_sensation_impaired_left': 'auc'},
    'aireadi_dyslipidaemia-diagnosis-biop': {'tg_ge_200': 'auc', 'total_cholesterol': 'mae', 'ldl_cholesterol': 'mae', 'hdl_cholesterol': 'mae'},
    'aireadi_foot-sensation-metabolic': {'foot_sensation_impaired_right': 'auc', 'foot_sensation_impaired_left': 'auc'},
    'aireadi_prior-hypertension-cardiovas': {'hypertension_history': 'auc'},
    'aireadi_visual-function-biopsychosoc': {'photopic_va_reduced_od': 'auc', 'photopic_va_reduced_os': 'auc', 'mesopic_va_reduced_od': 'auc', 'mesopic_va_reduced_os': 'auc', 'autorefraction_sphere_od': 'mae', 'autorefraction_cylinder_od': 'mae', 'autorefraction_sphere_os': 'mae', 'autorefraction_cylinder_os': 'mae'},
    'bdsp_arousal': {'high_arousal_index_15h': 'auc'},
    'bdsp_demographic-eeg': {'sex_female': 'auc', 'age_ge_65': 'auc', 'race_black': 'auc', 'deceased_6mo': 'auc'},
    'bdsp_depression-sleep': {'depressive_disorders': 'auc'},
    'bdsp_hf-sleep': {'heart_failure': 'auc'},
    'bdsp_snoring-demographic': {'osa_severity_ahi': 'qwk', 'low_sleep_efficiency': 'auc', 'reduced_rem': 'auc', 'reduced_n3': 'auc', 'high_arousal_index': 'auc', 'frequent_limb_movements': 'auc'},
    'bdsp_snoring-metrics': {'osa_severity_ahi': 'qwk', 'low_sleep_efficiency': 'auc', 'reduced_rem': 'auc', 'reduced_n3': 'auc', 'high_arousal_index': 'auc', 'frequent_limb_movements': 'auc'},
    'mimic_acute-renal-hospital': {'acute_renal_failure': 'auc'},
    'mimic_ckd-staging': {'lab_ckd': 'auc'},
    'mimic_coag-hemorrhagic': {'coagulation_hemorrhagic': 'auc'},
    'mimic_heart-failure-mm': {'heart_failure': 'auc'},
    'mimic_hf': {'heart_failure': 'auc'},
    'mimic_icu-stay-radiology': {'icu_admission': 'auc', 'in_hospital_death': 'auc'},
    'mimic_in-hospital-death-icu': {'in_hospital_death': 'auc', 'readmit_30d': 'auc', 'prolonged_stay_gt7d': 'auc', 'ed_revisit_30d': 'auc'},
    'mimic_sepsis-hospital': {'septicemia': 'auc'},
    'mimic_stroke-infarct-ed': {'cerebral_infarction': 'auc'},
}
BALANCE = {}  # S1's inline balance rule is `draw.balance`, not a target (Bosong, 2026-11-09)


@pytest.fixture(scope="module")
def converted(repo):
    return templates.convert(repo)


def _templates(outputs):
    return {d["template_id"]: d for rel, d in outputs.items() if rel.endswith("/template.yaml")}


def test_every_file_validates(converted):
    outputs, _ = converted
    for rel, data in outputs.items():
        if "/arms/" in rel:
            continue
        model = v1.TaskTemplate if rel.endswith("/template.yaml") else v1.Cohort
        c.load_data(data, model, rel)
    assert sum("/arms/" in r for r in outputs) == 5
    assert sum(r.endswith("/template.yaml") for r in outputs) == 30
    assert sorted(Path(r).name for r in outputs if "/cohorts/" in r).count("ladder.yaml") == 5
    assert sum(r.endswith("/cohorts/n20.yaml") for r in outputs) == 30


def test_ids_paths_and_mimic_renames(converted):
    outputs, _ = converted
    by_ds = {}
    for rel, d in outputs.items():
        if rel.endswith("/template.yaml"):
            assert rel == f"studio/datasets/{d['dataset']}/tasks/{d['template_id']}/template.yaml"
            assert d["template_id"].startswith(f"{d['dataset']}_")
            assert all(t["label"].startswith(f"{d['dataset']}:") for t in d["targets"])
            by_ds[d["dataset"]] = by_ds.get(d["dataset"], 0) + 1
    assert by_ds == {"aireadi": 15, "bdsp": 6, "mimic-iv": 9}
    assert set(templates.NAME_MAP.values()) == {t for t in _templates(outputs) if t.startswith("mimic-iv_")}
    assert all(k == "mimic_" + v.removeprefix("mimic-iv_") for k, v in templates.NAME_MAP.items())


def test_targets_and_metrics_are_v02s(converted):
    outputs, _ = converted
    tpl = _templates(outputs)
    inverse = {v: k for k, v in templates.NAME_MAP.items()}
    got = {inverse.get(t, t): {x["name"]: x["metric"] for x in d["targets"]} for t, d in tpl.items()}
    want = {t: {**v, **BALANCE.get(t, {})} for t, v in SCORED.items()}
    assert got == want
    assert len({n for v in SCORED.values() for n in v}) == 48


def test_cohorts_have_version_one(converted):
    outputs, _ = converted
    assert {d["version"] for rel, d in outputs.items() if "/cohorts/" in rel} == {"1.0"}


def test_u29_placement(converted):
    outputs, notes = converted
    for d in _templates(outputs).values():
        assert d["agent"]["statement"] and set(d["agent"]["environment"]) == set(templates.ENVIRONMENT)
        assert not set(d) & set(templates.DROPPED) and "data_mode" not in d
    assert sum(n["evidence"] == ["default", "full"] for n in notes.values()) == 28
    assert sum(bool(n["full_overrides"]) for n in notes.values()) == 7


def test_committed_tree_is_the_converter_output(repo, converted):
    outputs, _ = converted
    committed = {p.relative_to(repo).as_posix() for p in (repo / "studio/datasets").glob("*/tasks/*/**/*.yaml")
                 if p.relative_to(repo / "studio/datasets").parts[0] != "vitaldb"}  # written for v0.3, not converted
    assert committed == set(outputs)
    for rel, data in outputs.items():
        assert (repo / rel).read_text(encoding="utf-8") == templates.HEADER + convert.dump(data), rel


def test_conversion_is_stable(repo, tmp_path):
    a = convert.write(templates.convert(repo)[0], tmp_path / "a", templates.HEADER)
    b = convert.write(templates.convert(repo)[0], tmp_path / "b", templates.HEADER)
    assert [p.read_bytes() for p in a] == [p.read_bytes() for p in b]
