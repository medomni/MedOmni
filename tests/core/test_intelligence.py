"""Intelligences and open benchmarks (part 2b; R-76, R-77): contract shapes only."""
import json

import pytest

from medomni.core import contracts as c
from medomni.core import plugins
from medomni.core.cli import main

from .contract_examples import EXAMPLES, SCORE_RECORD
from .test_plugins import make_dist, make_plugin, site  # noqa: F401 - fixture

RUN = EXAMPLES["result-record"][0]
PRED = EXAMPLES["prediction-record"][0]


def _bad(data, model, match):
    with pytest.raises(c.ContractError, match=match):
        c.load_data(data, model)


def test_records_name_the_intelligence():
    run = c.load_data(RUN, c.RunRecord)
    assert (run.intelligence.kind, run.intelligence.name) == ("agent", "my-agent")
    assert run.agent.arm == "encoders" and run.agent.encoder_calls
    assert c.load_data(SCORE_RECORD, c.ScoreRecord).intelligence.kind == "agent"
    _bad({k: v for k, v in RUN.items() if k != "intelligence"} | {"agent": "my-agent"}, c.RunRecord, "intelligence")


def test_agent_fields_sit_in_the_agent_block():
    for moved in ("arm", "encoders_served", "encoder_calls", "files_opened"):
        _bad(RUN | {moved: RUN["agent"][moved]}, c.RunRecord, moved)
    _bad({k: v for k, v in RUN.items() if k != "agent"}, c.RunRecord, "agent")


def test_only_the_agent_kind_ships():
    _bad(RUN | {"intelligence": {"kind": "llm", "name": "x"}}, c.RunRecord, "kind")


def test_metric_names_come_from_the_registry():
    assert plugins.metric_names() == {"auc", "qwk", "mae"}
    _bad(SCORE_RECORD | {"metric": "brier"}, c.ScoreRecord, "unknown metric 'brier'.*auc, mae, qwk")


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


def test_benchmark_card():
    card = EXAMPLES["benchmark"][0]
    assert c.load_data(card, c.BenchmarkCard).accepts == ("agent",)
    _bad(card | {"accepts": []}, c.BenchmarkCard, "accepts")
    _bad(EXAMPLES["task-set"][0] | {"card": card}, c.TaskSet, "card")  # the card moved to the benchmark (R-83)


def test_benchmarks_are_plugin_content(site, repo, monkeypatch, capsys):  # noqa: F811
    import yaml

    make_plugin(site, "medomni-one", "fake_one",
                {"bench/benchmarks/their-bench/benchmark.yaml":
                     yaml.safe_dump(EXAMPLES["benchmark"][0] | {"name": "their-bench"}),
                 "bench/benchmarks/their-bench/sets/v1.yaml": yaml.safe_dump(EXAMPLES["task-set"][0] | {"name": "v1"})})
    kinds = plugins.content(plugins.roots(repo)[0])
    assert kinds["benchmarks"].pieces["their-bench"].full_name == "medomni-one:their-bench"
    monkeypatch.chdir(repo)
    main(["contracts", "check", "benchmarks", "sets"])
    out = capsys.readouterr().out
    assert "ok    medomni-one:bench/benchmarks/their-bench/benchmark.yaml" in out
    assert "ok    medomni-one:bench/benchmarks/their-bench/sets/v1.yaml" in out


def test_metrics_listed_by_medomni_plugins(capsys):
    """The three metric names point at Bench's scorer, which arrives in Stage 3 (Bosong, 2026-11-06)."""
    main(["plugins"])
    out = capsys.readouterr().out
    assert "medomni.metrics" in out and all(f"medomni:{m}" in out for m in ("auc", "qwk", "mae"))
