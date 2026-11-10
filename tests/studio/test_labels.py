"""The label evaluator (Recipes reference page): each rule kind on planted events. No data."""
import pytest

from medomni.studio.build.labels import anchor, label, match, window
from medomni.studio.build.contracts.recipe import Anchor, Label


def ev(t, code, value=None, visit=None):
    return {"time": t, "code": code, "numeric_value": value, "visit_id": visit}


def L(**kw):
    return Label.model_validate({"from": "any", "to": "any", **kw})


def ctx(events, event="ADM", **kw):
    return anchor(events, Anchor(event=event, **kw))


E = [ev("2150-01-01T00:00:00", "ADM", visit="1"), ev("2150-01-03T00:00:00", "DIS", visit="1"),
     ev("2150-01-02T00:00:00", "LAB", 3.0, "1"), ev("2150-01-02T12:00:00", "LAB", 5.0, "1"),
     ev("2150-02-01T00:00:00", "ADM", visit="2"), ev(None, "STATIC", 7.0)]


def test_code_match_is_exact_unless_a_regex():
    assert match("DIAGNOSIS//ICD//N179", "^DIAGNOSIS//ICD//(N17|584)")
    assert not match("LAB//1", "LAB") and match("LAB", "LAB")


def test_anchor_first_last_plus_and_none():
    assert ctx(E).visit == "1"
    assert ctx(E, pick="last").visit == "2"
    assert str(ctx(E, plus="24 hours").anchor) == "2150-01-02 00:00:00"
    assert ctx(E, event="NOPE") is None


@pytest.mark.parametrize("pick,want", [("first", 3.0), ("last", 5.0), ("min", 3.0), ("max", 5.0)])
def test_value_pick(pick, want):
    assert label(L(value="LAB", pick=pick), ctx(E)) == want


def test_exists_and_none():
    assert label(L(exists="LAB"), ctx(E)) == 1 and label(L(exists="XX"), ctx(E)) == 0
    assert label(L(none="XX"), ctx(E)) == 1 and label(L(none="LAB"), ctx(E)) == 0


def test_op_bins_default():
    assert label(L(value="LAB", op=">=", x=5), ctx(E)) == 1
    assert label(L(value="LAB", bins=(1, 4, 9)), ctx(E)) == 2  # 5.0 is past 2 of the 3 edges
    assert label(L(value="XX"), ctx(E)) is None
    assert label(L(value="XX", default=0), ctx(E)) == 0


def test_cases_take_the_first_hit_and_else():
    r = L(cases=({"when": {"exists": "XX"}, "then": 2}, {"when": {"exists": "LAB"}, "then": 1}), **{"else": 0})
    assert label(r, ctx(E)) == 1
    r = L(cases=({"when": {"value": "XX", "op": "==", "x": 1}, "then": 2},), **{"else": 0})
    assert label(r, ctx(E)) is None  # no case had a value


def test_windows_ends_and_offsets():
    rule = Label.model_validate({"exists": "LAB", "from": "anchor", "to": "anchor + 1 days"})
    assert len(window(ctx(E), rule, "LAB")) == 1  # 02T00:00 is on the end, 02T12:00 past it
    rule = Label.model_validate({"exists": "LAB", "from": "anchor", "to": "anchor + 1 days", "include_to": False})
    assert window(ctx(E), rule, "LAB") == []


def test_untimed_events_count_only_from_the_start():
    assert label(L(exists="STATIC"), ctx(E)) == 1
    assert label(Label.model_validate({"exists": "STATIC", "from": "anchor", "to": "any"}), ctx(E)) == 0


def test_visit_scope_and_visit_times():
    assert label(L(exists="ADM", other_visit=True), ctx(E)) == 1
    assert label(L(exists="LAB", other_visit=True), ctx(E)) == 0
    assert label(L(exists="ADM", same_visit=True), ctx(E, pick="last")) == 1
    rule = Label.model_validate({"exists": "ADM", "from": "visit:DIS", "to": "visit:DIS + 31 days", "other_visit": True})
    assert label(rule, ctx(E)) == 1
    rule = Label.model_validate({"exists": "ADM", "from": "visit:NOPE", "to": "any"})
    assert label(rule, ctx(E)) is None  # the visit event is missing


def test_cross_sectional_anchor_counts_everything():
    es = [ev(None, "VISIT"), ev(None, "OMOP//x", 1.0)]
    assert label(Label.model_validate({"value": "OMOP//x", "from": "any", "to": "anchor"}), ctx(es, event="VISIT")) == 1.0
