"""Contract models: valid files load as frozen objects; wrong files are refused with the field named; schemas match."""
import copy
import json

import jsonschema
import pytest
from pydantic import ValidationError

from medomni.core import contracts as c
from medomni.core.contracts import schemas

from .contract_examples import EXAMPLES, SCORE_RECORD

BY_FILE = {s.file: s for s in c.SCHEMAS}


def test_sixteen_contracts():
    assert len(c.CONTRACTS) == 16
    assert set(BY_FILE) == set(EXAMPLES)


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_valid_instance_loads_frozen(name):
    data, _ = EXAMPLES[name]
    obj = c.load_data(data, BY_FILE[name].model, name)
    root = obj.root if hasattr(obj, "root") else obj
    fields = getattr(type(root), "model_fields", {})
    if fields:
        field = next(iter(fields))
        with pytest.raises(ValidationError):
            setattr(root, field, None)


# A label library's top-level keys are label names, so it has no unknown top-level field
@pytest.mark.parametrize("name", sorted(k for k in EXAMPLES if k != "recipe-labels"))
def test_unknown_field_is_named(name):
    data = copy.deepcopy(EXAMPLES[name][0])
    data["not_a_field"] = 1
    with pytest.raises(c.ContractError) as e:
        c.load_data(data, BY_FILE[name].model, f"{name}.yaml")
    assert "not_a_field" in str(e.value) and f"{name}.yaml" in str(e.value)


@pytest.mark.parametrize("name", sorted(k for k, (_, req) in EXAMPLES.items() if req))
def test_missing_required_field_is_named(name):
    data, req = copy.deepcopy(EXAMPLES[name][0]), EXAMPLES[name][1]
    del data[req]
    with pytest.raises(c.ContractError) as e:
        c.load_data(data, BY_FILE[name].model, name)
    assert any(field.split(".")[-1] == req or req in field for field, _ in e.value.problems), e.value


def test_wrong_type_is_refused_not_coerced():
    data = copy.deepcopy(EXAMPLES["family"][0])
    data["protocol"]["ndim"] = "1"
    with pytest.raises(c.ContractError, match="protocol.ndim"):
        c.load_data(data, c.FamilyFile)


def test_schemas_are_current():
    rendered = schemas.render()
    on_disk = {p.name: p.read_text(encoding="utf-8") for p in schemas.HERE.glob("*.schema.json")}
    assert rendered == on_disk, "run: python -m medomni.core.contracts.schemas"


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_schema_agrees_with_model(name):
    schema = json.loads(schemas.render()[f"{name}.schema.json"])
    data, req = EXAMPLES[name]
    jsonschema.validate(data, schema)
    if req:
        bad = copy.deepcopy(data)
        del bad[req]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


def test_score_record_is_a_result_record():
    assert c.load_data(SCORE_RECORD, c.ResultRecord).kind == "score"


def test_load_reads_yaml_and_json(tmp_path):
    (tmp_path / "a.yaml").write_text("name: x\nscaffold: s\nmodel: m\nroute: local\nmodel_served: m\n")
    (tmp_path / "a.json").write_text(json.dumps(EXAMPLES["agent-config"][0]))
    (tmp_path / "bad.yaml").write_text("name: [unclosed\n")
    assert c.load(tmp_path / "a.yaml", c.AgentConfig).route == "local"
    assert c.load(tmp_path / "a.json", c.AgentConfig).route == "cloud"
    with pytest.raises(c.ContractError, match="cannot parse"):
        c.load(tmp_path / "bad.yaml", c.AgentConfig)


def refused(name, change, match):
    data = copy.deepcopy(EXAMPLES[name][0])
    change(data)
    with pytest.raises(c.ContractError, match=match):
        c.load_data(data, BY_FILE[name].model, name)


def test_rules_inside_contracts():
    refused("family", lambda d: d["protocol"].update(range=[100, 0]), "min < max")
    refused("family", lambda d: d["protocol"].update(dtype="int64"), "dtype")
    refused("aliases", lambda d: d["families"]["ecg-1lead-200hz-uv"]["accepts"].append("missing"), "unknown vocab")
    refused("agent-config", lambda d: d["env"].update(OPENAI_API_KEY="sk-literal"), "only as")
    refused("task-template", lambda d: d.update(template_id="other_aki"), "does not start with its dataset")
    refused("task-template", lambda d: d.update(variants=["full"]), "include default")
    refused("task-template", lambda d: d["targets"][0].update(metric="f1"), "metric")
    refused("task-set", lambda d: d["tasks"].append(d["tasks"][0]), "twice")
    refused("task-set", lambda d: d["tasks"][0].update(task="dummy_aki"), "template>@<cohort")
    refused("task-set", lambda d: d["tasks"][0].update(fingerprint="sha256:" + "0" * 64), "fingerprint")
    refused("recipe", lambda d: d["require"][0].update({"from": "yesterday"}), "not a time")
    refused("recipe-labels", lambda d: d["aki"].pop("to"), "from and to")
    refused("recipe-labels", lambda d: d["aki"].update(value="LAB//x"), "exactly one")
    refused("model-card", lambda d: d.update(family="other-family"), "does not start with its family")
    refused("workspace-config", lambda d: d.update(cache="relative/cache"), "absolute")


def test_local_agent_may_hold_a_placeholder():
    data = copy.deepcopy(EXAMPLES["agent-config"][0]) | {"route": "local", "env": {"OPENAI_API_KEY": "no-key"}}
    assert c.load_data(data, c.AgentConfig).route == "local"
