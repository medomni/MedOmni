"""The scorer, the replay agent end to end (check 7) and the Harbor runner's records. No model, no Harbor, no real data."""
import importlib
import json
from pathlib import Path

import pytest
import yaml

from medomni.bench import metrics, runs as runs_mod, scoring
from medomni.studio import build as b
from medomni.studio.build import checks
from medomni.core import workspace
from medomni.core.contracts import RunRecord, ScoreRecord, TaskSet, load_data, load_lines
from medomni.core.families.dummy.datasets import make_dataset

pool_mod = importlib.import_module("medomni.studio.build.pool")
REPO = Path(__file__).resolve().parents[2]
PAIR = "aireadi_crp-white-cell-count@n20"
SET = "medomni-bench/smoke-dummy"


# ---- metrics and the rules
def test_metrics():
    assert metrics.auc([(1, 0.9), (0, 0.1)]) == 1.0 and metrics.auc([(1, 0.5), (0, 0.5)]) == 0.5
    assert metrics.auc([(1, 0.9), (1, 0.1)]) is None  # one class: unscorable, never 0
    assert metrics.mae([(1.0, 2.0), (3.0, 3.0)]) == 0.5
    assert metrics.qwk([(0, 0), (1, 1), (2, 2)]) == 1.0


def outcome(preds, failed=(), metric="auc"):
    gold = {"t": {"a": 1.0, "b": 0.0}}
    return scoring.score_targets({"t": metric}, gold, preds, set(failed))


def test_an_agent_failure_is_imputed_at_chance():
    assert outcome({"a": {"t": 0.9}, "b": {}}, failed=["b"]).values["t"]["value"] == 1.0


def test_a_failure_has_nothing_to_impute_on_a_value():
    o = outcome({"a": {"t": 1.0}, "b": {}}, failed=["b"], metric="mae")
    assert o.values["t"]["n"] == 1 and any("incomplete" in f for f in o.flags)


def test_a_missing_prediction_refuses():
    with pytest.raises(scoring.Refused):
        outcome({"a": {"t": 0.9}, "b": {}})


def test_constant_predictions_are_flagged():
    assert any("constant" in f for f in outcome({"a": {"t": 0.5}, "b": {"t": 0.5}}).flags)


# ---- the replay agent, end to end
@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("runs")
    mp = pytest.MonkeyPatch()
    mp.setattr(checks, "MIN_PER_CLASS", 1)
    mp.setattr(pool_mod, "label", lambda rule, ctx, hooks=None: int(ctx.events[0]["subject_id"][-1]) % 2)
    copy = make_dataset(REPO / "studio/datasets/aireadi", root / "aireadi", subjects=30)
    cfg = root / "workspace.yaml"
    cfg.write_text(f"datasets: {{aireadi: {{path: {copy.root}}}}}\ncache: {root}/cache\ntasks: {root}/tasks\nruns: {root}/runs\n"
                   f"results: {root}/results.jsonl\nkeys_file: {root}/keys.env\nhf_cache: {root}/hf\n")
    ws = workspace.load(cfg)
    b.build([PAIR], ["encoders"], ws=ws, draw_with=lambda r: sorted(r.patients)[:12])
    task_set = load_data({"name": "smoke-dummy", "builder": "medomni-v1", "arms": ["encoders"], "tasks": [{"task": PAIR, "version": 1}]}, TaskSet, "x")
    mp.setattr(runs_mod, "load_set", lambda name: (task_set, None))
    yield ws
    mp.undo()


def test_the_replay_agent_runs_a_set_and_it_scores(built):
    job = runs_mod.run(SET, "terminus-2-replay", ws=built)[0]
    assert len(load_lines(job / "runs.jsonl", RunRecord)) == 12
    assert runs_mod.score(SET, ws=built) == 0
    rows = load_lines(Path(built.results), ScoreRecord)
    assert {r.target for r in rows} == {"hs_crp_ge_3", "wbc_value"}
    assert all(r.config_hash.startswith("cfg1:") and r.n_atoms == 12 for r in rows)
    auc = next(r for r in rows if r.metric == "auc")
    assert auc.value == 0.5 and any("constant" in f for f in auc.flags)  # every prediction is the same 0.5


def test_a_later_row_replaces_an_earlier_one(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text('{"run_id": "a", "value": 1}\n{"run_id": "a", "value": 2}\n')
    assert scoring.latest(p)["a"]["value"] == 2


def test_an_infrastructure_failure_refuses_the_cell_with_no_number(built, tmp_path):
    src = sorted(Path(built.runs).glob("*--*"))[0]
    job = tmp_path / src.name
    job.mkdir()
    lines = (src / "runs.jsonl").read_text().splitlines()
    first = json.loads(lines[0])
    first["error_kind"] = "infra"
    (job / "runs.jsonl").write_text("\n".join([json.dumps(first), *lines[1:]]) + "\n")
    (job / "predictions.jsonl").write_text((src / "predictions.jsonl").read_text())
    rows = scoring.score_run(job, Path(built.tasks) / "atomtasks/_content", "0" * 64, tmp_path / "res.jsonl")
    assert rows and all(r.get("value") is None and "refused" in r["flags"][0] for r in rows)


def test_mixed_config_hashes_are_flagged_in_a_table():
    base = {"task_set": "b/s", "target": "t", "metric": "auc"}
    assert scoring.flag_configured_differently([{**base, "config_hash": "x"}, {**base, "config_hash": "y"}])
    assert not scoring.flag_configured_differently([{**base, "config_hash": "x"}, {**base, "config_hash": "x"}])


# ---- the Harbor runner's records (nothing launched)
def test_harbor_job_file_and_collect(built, tmp_path):
    h = importlib.import_module("medomni.bench.runs.harbor")
    agent = runs_mod.load_agent("terminus-2-luna")
    from medomni.studio.build import _arm

    ws = built.model_copy(update={"runs": str(tmp_path)})
    job = runs_mod.Job(ws, SET, agent, _arm("encoders"), None, stamp="20261109-000000")
    h.harness.prepare(job)
    doc = yaml.safe_load((job.folder / "job.yaml").read_text())
    assert doc["job_name"] == job.name and doc["jobs_dir"] == str(tmp_path) and len(doc["tasks"]) == 12
    assert doc["agents"][0]["model_name"] == agent.model
    pair, atom, d = job.atoms()[0]
    t = job.folder / "trial-1"
    (t / "verifier").mkdir(parents=True)
    (t / "agent").mkdir()
    (t / "result.json").write_text(json.dumps({"task_id": {"path": str(d)}, "exception_info": None}))
    (t / "verifier/submission.csv").write_text("target,prediction\nhs_crp_ge_3,0.7\nwbc_value,6.0\n")
    (t / "agent/trajectory.json").write_text(json.dumps({"steps": [{"model_name": "gpt-6-luna"}]}))
    h.harness.collect(job)
    assert '"value": 0.7' in (job.folder / "predictions.jsonl").read_text()
    assert json.loads((job.folder / "runs.jsonl").read_text().splitlines()[0])["model_served"] == "gpt-6-luna"


def test_error_classes():
    from medomni.bench.runs.harbor import classify_error

    assert classify_error(None) is None
    assert classify_error({"exception_type": "AgentTimeoutError"}) == "agent"
    assert classify_error({"exception_type": "SomethingNew"}) == "infra"  # unknown is ours: never score what we don't understand


def test_an_arm_from_outside_builds_and_runs_with_no_core_or_bench_change(built, tmp_path, monkeypatch):
    """Check 6, R-85, R-143: an arm is one registered name; its run side is in medomni.arms, and its build side for the
    v1 builder in medomni.arm_builds. Nothing lists arm names."""
    from medomni.bench.arms import Arm
    from medomni.core import plugins
    from medomni.studio.build.arms import ArmBuild

    outside = Arm("outside-arm", "Registered by an outside package.", perception="off", max_calls=None)
    outside_build = ArmBuild("outside-arm", tools_block="tools.noenc.md")
    real = plugins.resolve

    def resolve(group):
        out = real(group)
        add = {plugins.ARMS: ("outside-arm", outside), plugins.ARM_BUILDS: ("medomni-v1:outside-arm", outside_build)}.get(group)
        if add:
            piece = type("P", (), {"load": staticmethod(lambda obj=add[1]: obj)})()
            return type(out)(**{**out.__dict__, "pieces": {**out.pieces, add[0]: piece}})
        return out

    monkeypatch.setattr(plugins, "resolve", resolve)
    real_names = plugins.arm_names
    monkeypatch.setattr(plugins, "arm_names", lambda: real_names() | {"outside-arm"})
    ws = built.model_copy(update={"runs": str(tmp_path / "runs")})
    b.build([PAIR], ["encoders", "outside-arm"], ws=ws, draw_with=lambda r: sorted(r.patients)[:12])
    assert sorted(p.name for p in (Path(ws.tasks) / "atomtasks/outside-arm").iterdir())
    task_set = TaskSet.model_construct(name="s", builder="medomni-v1", arms=("encoders", "outside-arm"), tasks=runs_mod.load_set(SET)[0].tasks)
    monkeypatch.setattr(runs_mod, "load_set", lambda name: (task_set, None))
    job = runs_mod.run(SET, "terminus-2-replay", arms=["outside-arm"], ws=ws)[0]
    assert (job / "predictions.jsonl").read_text()
