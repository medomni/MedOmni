"""The v1 task template (part 2b; R-76, R-77, R-147): the agent's parts sit in its agent block; metrics are registered."""
import pytest

from medomni.core import contracts as c
from medomni.studio.build.contracts import TaskTemplate

from .contract_examples import EXAMPLES

TEMPLATE = EXAMPLES["task-template"][0]


def _bad(data, match):
    with pytest.raises(c.ContractError, match=match):
        c.load_data(data, TaskTemplate)


def test_template_keeps_agent_parts_in_its_agent_block():
    t = c.load_data(TEMPLATE, TaskTemplate)
    assert t.agent.submission_path.endswith("predictions.csv") and t.agent.environment.cpus == 2
    for moved in ("instruction", "environment", "submission_path"):
        _bad(TEMPLATE | {moved: TEMPLATE["agent"][moved]}, moved)
    _bad({k: v for k, v in TEMPLATE.items() if k != "agent"}, "agent")


def test_template_metrics_come_from_the_registry():
    _bad(dict(TEMPLATE, targets=[{"name": "aki", "label": "dummy:aki", "metric": "brier"}]), "unknown metric 'brier'.*auc, mae, qwk")
