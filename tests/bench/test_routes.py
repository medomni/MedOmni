"""The route check: an agent's route against each dataset policy of the set, before a run (Bosong, 2026-11-10)."""
import json

import pytest

from medomni.bench.runs import routes
from medomni.core.contracts import DatasetPolicy, load, load_data
from medomni.core.loading import find_package
from medomni.core.tasks import layout

from tests.core.contract_examples import EXAMPLES

POLICY = EXAMPLES["dataset-policy"][0]


def _tree(tmp_path, datasets_by_task):
    for task, datasets in datasets_by_task.items():
        d = layout.content_dir(tmp_path, task)
        d.mkdir(parents=True)
        (d / "content.json").write_text(json.dumps({"version": "1.0", "datasets": datasets,
                                                    "targets": [{"name": "y", "metric": "auc"}],
                                                    "atoms": [{"atom": "a", "subject": "1"}]}))
    return tmp_path


@pytest.fixture
def policies(monkeypatch):
    table = {}

    def policy(ds):
        return None if table.get(ds) is None else load_data(POLICY | {"dataset": ds, "routes": table[ds][0],
                                                                       "route_conditions": table[ds][1]}, DatasetPolicy)

    monkeypatch.setattr(routes, "_policy", policy)
    return table


def test_allow_conditional_deny(tmp_path, policies):
    policies.update({"open": ({"local": "allow", "cloud": "allow"}, {}),
                     "cond": ({"local": "allow", "cloud": "conditional"}, {"cloud": "a signed agreement"}),
                     "closed": ({"local": "allow", "cloud": "deny"}, {})})
    tree = _tree(tmp_path, {"t1": ["open"], "t2": ["cond", "open"], "t3": ["closed"]})
    assert routes.check(tree, ["t1", "t2"], "cloud") == ([], ["cond, cloud route: a signed agreement"])
    assert routes.check(tree, ["t1", "t2", "t3"], "cloud")[0] == ["route: closed's policy denies the cloud route"]
    assert routes.check(tree, ["t1", "t2", "t3"], "local") == ([], [])


def test_unknown_rules_refuse_all_but_local(tmp_path, policies):
    tree = _tree(tmp_path, {"t1": [], "t2": ["nopolicy"]})
    refused, _ = routes.check(tree, ["t1", "t2"], "cloud")
    assert refused == ["route: t1 names no dataset, so a cloud route can't be checked",
                       "route: nopolicy has no policy.yaml, so a cloud route can't be checked"]
    assert routes.check(tree, ["t1", "t2"], "local") == ([], [])


def test_preflight_refuses_a_denied_route(tmp_path, policies, monkeypatch, capsys):
    from medomni.bench import runs

    policies.update({"closed": ({"local": "allow", "cloud": "deny"}, {}),
                     "cond": ({"local": "allow", "cloud": "conditional"}, {"cloud": "zero retention"})})
    monkeypatch.setattr(runs, "task_checks", lambda tree, task, arms: [])
    from medomni.bench.scoring import standins

    monkeypatch.setattr(standins, "problems", lambda tree, task: [])  # these tasks have no answers to score
    tree = _tree(tmp_path, {"t1": ["cond"], "t2": ["closed"]})
    entry = lambda t: type("E", (), {"task": t})()  # noqa: E731
    with pytest.raises(runs.RunError, match="denies the cloud route"):
        runs.preflight(tree, type("S", (), {"tasks": [entry("t1"), entry("t2")]})(), ["encoders"], "cloud")
    runs.preflight(tree, type("S", (), {"tasks": [entry("t1")]})(), ["encoders"], "cloud")
    assert "condition: cond, cloud route: zero retention" in capsys.readouterr().out


def test_shipped_policies_allow_local_and_name_every_cloud_condition():
    for ds in ("aireadi", "bdsp", "mimic-iv", "vitaldb"):
        p = load(find_package(ds) / "policy.yaml", DatasetPolicy)
        assert p.routes.local == "allow" and p.routes.cloud != "deny", ds  # BDSP: written approval (Bosong, 2026-11-10)
        if p.routes.cloud == "conditional":
            assert p.route_conditions.get("cloud"), ds
