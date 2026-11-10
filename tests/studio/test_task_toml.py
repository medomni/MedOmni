"""task.toml's `allow_internet` comes from the template. Harbor reads `false` as a request for its own egress-control
sidecar (built with docker buildx); the atom's network is closed either way by `atomnet {internal: true}`."""
import tomllib
from types import SimpleNamespace as NS

import pytest

from medomni.studio.build import render


@pytest.mark.parametrize("allow", [True, False])
def test_allow_internet_follows_the_template(allow):
    env = NS(cpus=2, memory_mb=4096, allow_internet=allow, agent_timeout_sec=60, verifier_timeout_sec=30)
    template = NS(agent=NS(environment=env, submission_path="/workspace/submission/predictions.csv"),
                  template_id="t", targets=[NS(name="y")])
    pair = NS(template=template, id="p", dataset="d", config=NS(storage_mb=None), cohort_name="c")
    doc = tomllib.loads(render.task_toml(pair, NS(name="encoders"), None, "s", "2020-01-01 00:00:00"))
    assert doc["environment"]["allow_internet"] is allow
    assert doc["metadata"]["network"] == "closed:atomnet-internal"
