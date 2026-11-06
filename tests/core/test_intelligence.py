"""Intelligences and open benchmarks (part 2b; R-76, R-77): contract shapes only."""
import json

import pytest

from medomni.core import contracts as c
from medomni.core import plugins
from medomni.core.cli import main

from .contract_examples import EXAMPLES, SCORE_RECORD
from .test_plugins import make_dist, make_plugin, site  # noqa: F401 - fixture

RUN = EXAMPLES["result-record"][0]
TEMPLATE = EXAMPLES["task-template"][0]
PRED = EXAMPLES["prediction-record"][0]


def _bad(data, model, match):
    with pytest.raises(c.ContractError, match=match):
        c.load_data(data, model)


def test_records_name_the_intelligence():
    run = c.load_data(RUN, c.RunRecord)
    assert (run.intelligence.kind, run.intelligence.name) == ("agent", "my-agent")
    assert run.agent.condition == "enc" and run.agent.encoder_calls
    assert c.load_data(SCORE_RECORD, c.ScoreRecord).intelligence.kind == "agent"
    _bad({k: v for k, v in RUN.items() if k != "intelligence"} | {"agent": "my-agent"}, c.RunRecord, "intelligence")


def test_agent_fields_sit_in_the_agent_block():
    for moved in ("condition", "encoders_served", "encoder_calls", "files_opened"):
        _bad(RUN | {moved: RUN["agent"][moved]}, c.RunRecord, moved)
    _bad({k: v for k, v in RUN.items() if k != "agent"}, c.RunRecord, "agent")


def test_only_the_agent_kind_ships():
    _bad(RUN | {"intelligence": {"kind": "llm", "name": "x"}}, c.RunRecord, "kind")


def test_template_keeps_agent_parts_in_its_agent_block():
    t = c.load_data(TEMPLATE, c.TaskTemplate)
    assert t.agent.submission_path.endswith("predictions.csv") and t.agent.environment.cpus == 2
    for moved in ("instruction", "environment", "submission_path"):
        _bad(TEMPLATE | {moved: TEMPLATE["agent"][moved]}, c.TaskTemplate, moved)
    _bad({k: v for k, v in TEMPLATE.items() if k != "agent"}, c.TaskTemplate, "agent")


def test_metric_names_come_from_the_registry():
    assert plugins.metric_names() == {"auc", "qwk", "mae"}
    bad = dict(TEMPLATE, targets=[{"name": "aki", "label": "dummy:aki", "metric": "brier"}])
    _bad(bad, c.TaskTemplate, "unknown metric 'brier'.*auc, mae, qwk")
    _bad(SCORE_RECORD | {"metric": "brier"}, c.ScoreRecord, "unknown metric")


def test_a_registered_metric_is_accepted(site):  # noqa: F811
    make_dist(site, "medomni-one", "fake_one", {plugins.METRICS: {"brier": "fake_one:OBJ"}})
    c.load_data(SCORE_RECORD | {"metric": "brier"}, c.ScoreRecord)


@pytest.mark.parametrize("value", [0.82, 3, "stage-2"])
def test_prediction_values(value):
    assert c.load_data(PRED | {"value": value}, c.PredictionRecord).value == value


@pytest.mark.parametrize("value", [True, "", None, float("nan")])
def test_prediction_values_refused(value):
    with pytest.raises(c.ContractError):
        c.load_data(PRED | {"value": value}, c.PredictionRecord)


def test_predictions_file_names_the_bad_line(tmp_path):
    p = tmp_path / "predictions.jsonl"
    good = json.dumps(PRED)
    p.write_text(good + "\n" + json.dumps(PRED | {"value": True}) + "\n")
    with pytest.raises(c.ContractError, match="predictions.jsonl:2"):
        c.load_lines(p, c.PredictionRecord)
    p.write_text(good + "\n\n" + good + "\n")
    assert len(c.load_lines(p, c.PredictionRecord)) == 2


def test_task_set_card():
    s = c.load_data(EXAMPLES["task-set"][0], c.TaskSet)
    assert s.card.accepts == ("agent",)
    no_card = {k: v for k, v in EXAMPLES["task-set"][0].items() if k != "card"}
    assert c.load_data(no_card, c.TaskSet).card is None
    _bad(EXAMPLES["task-set"][0] | {"card": dict(s.card.model_dump(), accepts=[])}, c.TaskSet, "accepts")


def test_task_sets_are_plugin_content(site, repo, monkeypatch, capsys):  # noqa: F811
    import yaml

    make_plugin(site, "medomni-one", "fake_one",
                {"bench/sets/their-bench.yaml": yaml.safe_dump(EXAMPLES["task-set"][0] | {"name": "their-bench"})})
    kinds = plugins.content(plugins.roots(repo)[0])
    assert kinds["sets"].pieces["their-bench"].full_name == "medomni-one:their-bench"
    monkeypatch.chdir(repo)
    main(["contracts", "check", "sets"])
    assert "ok    medomni-one:bench/sets/their-bench.yaml" in capsys.readouterr().out


def test_metrics_listed_by_medomni_plugins(capsys):
    """The three metric names point at Bench's scorer, which arrives in Stage 3 (Bosong, 2026-11-06)."""
    main(["plugins"])
    out = capsys.readouterr().out
    assert "medomni.metrics" in out and all(f"medomni:{m}" in out for m in ("auc", "qwk", "mae"))
