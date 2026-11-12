"""The task-correctness checks on v0.2's synthetic must-fail fixtures and on planted cases (R-119, R-121). No data."""
import csv
import json
from pathlib import Path

import pytest
import yaml

from medomni.studio.build import checks, content
from medomni.studio.build.labels import anchor
from medomni.studio.build.pool import Patient, Pool, load_pair

FIX = Path(__file__).parent / "fixtures/checks"
EXPECT = yaml.safe_load((FIX / "EXPECTATIONS.yaml").read_text())


def cases(gate):
    return [(k, v["verdict"]) for k, v in EXPECT[gate].items() if isinstance(v, dict) and "verdict" in v]


def parent(case: Path) -> dict:
    return json.loads(next(case.glob("parents/*/parent.json")).read_text())


def table(case: Path, sid: str, name: str):
    p = next(case.glob(f"*__{sid}__*")) / "data/tables" / name
    if not p.exists():
        return None
    rows = list(csv.reader(open(p, newline="")))
    return {"head": rows[0], "rows": rows[1:]}


def ev(t, code, visit):
    return {"time": t, "code": code, "numeric_value": None, "visit_id": visit}


def _pool(pair, patients):
    return Pool(pair, {p.id: p for p in patients}, {})


@pytest.mark.parametrize("name,verdict", cases("t1-eligible"))
def test_eligible(name, verdict):
    pair, case = load_pair("mimic-iv_in-hospital-death-icu@n20"), FIX / "t1-eligible" / name
    patients = []
    for sid, st in parent(case)["index_stay"].items():
        events = [ev(st["admit"], "MIMIC//ADMISSION", st["hadm_id"])]
        events += [ev(st["disch"], "MIMIC//DISCHARGE", st["hadm_id"])] if st["disch"] else []
        events += [ev(st["death"], "MIMIC//DEATH", st["hadm_id"])] if st["death"] else []
        patients.append(Patient(sid, anchor(events, pair.cohort.anchor), {}, {}))
    got = checks.eligible(_pool(pair, patients), [p.id for p in patients])
    assert bool(got) == (verdict == "RED")


@pytest.mark.parametrize("name,verdict", cases("t1-leak"))
def test_no_answer_in_the_evidence(name, verdict):
    pair, case = load_pair("mimic-iv_in-hospital-death-icu@n20"), FIX / "t1-leak" / name
    recs = {}
    for sid, st in parent(case)["index_stay"].items():
        tables = {n: t for n in ("admissions", "diagnoses_icd") if (t := table(case, sid, f"{n}.csv"))}
        recs[sid] = {"tables": tables, "index_visit": st["hadm_id"]}
    assert bool(checks.leak(pair, recs, content.table_specs(pair))) == (verdict == "RED")


@pytest.mark.parametrize("name,verdict", cases("t1-eventgate"))
def test_events_still_ahead(name, verdict):
    pair, case = load_pair("mimic-iv_icu-stay-radiology@n20"), FIX / "t1-eventgate" / name
    p, patients = parent(case), []
    for sid, b in p["boundaries"].items():
        at = p["event_times"]["icu_admission"].get(sid)
        events = [ev(b, "MIMIC//ADMISSION", "v1")] + ([ev(at, "MIMIC//ICU_ADMISSION", "v1")] if at else [])
        patients.append(Patient(sid, anchor(events, pair.cohort.anchor), {"icu_admission": int(bool(at)), "in_hospital_death": 0}, {}))
    assert bool(checks.events_ahead(_pool(pair, patients), [x.id for x in patients])) == (verdict == "RED")


@pytest.mark.parametrize("name,verdict", cases("t1-constgold"))
def test_answers_that_vary(name, verdict):
    stats = parent(FIX / "t1-constgold" / name)["pool_stats"]
    assert bool(checks.answers_vary(stats)) == (verdict == "RED")  # a FLAG is reported elsewhere, and does not refuse


def _short_pool(drawn_on, answers):
    pair = load_pair(f"{drawn_on}@n20")
    return pair, _pool(pair, [Patient(str(i), None, a, {}) for i, a in enumerate(answers)])


def test_a_short_target_is_marked_and_a_short_drawn_target_is_refused():
    pair, result = _short_pool("mimic-iv_in-hospital-death-icu", [
        {"in_hospital_death": i % 2, "readmit_30d": int(i == 0), "prolonged_stay_gt7d": i % 2, "ed_revisit_30d": 0} for i in range(20)])
    problems, marks = checks.enough_patients(result, [str(i) for i in range(20)])
    assert not problems and set(marks) == {"readmit_30d", "ed_revisit_30d"}
    assert marks["readmit_30d"]["reason"] == "fewer than 5 in a class"
    _, result = _short_pool("mimic-iv_in-hospital-death-icu", [
        {"in_hospital_death": int(i < 2), "readmit_30d": i % 2, "prolonged_stay_gt7d": i % 2, "ed_revisit_30d": i % 2} for i in range(20)])
    problems, _ = checks.enough_patients(result, [str(i) for i in range(20)])
    assert any("in_hospital_death" in p for p in problems)
