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


def test_fifteen_contracts():
    # the fingerprint left (R-111); the benchmark came (R-83); the built task (R-143); recipe, task template and task
    # proposal went to Studio (R-147)
    assert len(c.CONTRACTS) == 14
    assert "benchmark" in c.CONTRACTS and not {"fingerprint", "recipe", "task template", "task proposal"} & set(c.CONTRACTS)
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


# Built-task files are open, since a builder may write its own fields beside the contract's (R-143)
@pytest.mark.parametrize("name", sorted(k for k in EXAMPLES if not k.startswith("built-")))
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
    (tmp_path / "a.yaml").write_text("name: x\nmodel: m\nroute: local\n")
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
    refused("task-set", lambda d: d["tasks"].append(d["tasks"][0]), "twice")
    refused("task-set", lambda d: d["tasks"][0].update(task="dummy aki"), "tasks.0.task")  # any id but no whitespace (R-147)
    refused("task-set", lambda d: d["tasks"][0].update(task=""), "tasks.0.task")
    refused("task-set", lambda d: d["tasks"][0].update(fingerprint="fp1:" + "0" * 64), "fingerprint")  # R-111
    refused("task-set", lambda d: d["tasks"][0].update(version=-1), "version")
    refused("task-set", lambda d: d.update(arms=["encoders", "encoders"]), "arm appears twice")
    refused("task-set", lambda d: d.update(arms=["my-arm"]), "unknown arm")
    refused("task-set", lambda d: d.update(arms=[]), "arms")
    refused("result-record", lambda d: d.update(config_hash="v0.2:" + "0" * 64), "v0.2:")
    refused("result-record", lambda d: d.update(task_version="0.0"), "v0.2:")
    refused("result-record", lambda d: d.update(task_set="smoke-dummy"), "task_set")
    refused("result-record", lambda d: d["agent"].update(arm="enc"), "unknown arm")
    refused("model-card", lambda d: d.update(family="other-family"), "does not start with its family")
    refused("workspace-config", lambda d: d.update(cache="relative/cache"), "absolute")


def test_core_reads_no_runner_settings():
    """R-145: Core's agent config holds kind, name, model and route; `settings` are the runner's, unread here."""
    data = copy.deepcopy(EXAMPLES["agent-config"][0])
    data["settings"]["anything"] = {"a runner": "decides"}
    assert c.load_data(data, c.AgentConfig).settings["anything"]


def test_imported_v02_record_carries_a_stand_in():
    data = copy.deepcopy(EXAMPLES["result-record"][0]) | {"task_version": "0.0", "config_hash": "v0.2:" + "0" * 64}
    assert c.load_data(data, c.RunRecord).config_hash.startswith("v0.2:")


def test_arm_variant_is_its_own_field():
    data = copy.deepcopy(EXAMPLES["result-record"][0])
    data["agent"] |= {"arm": "modality-ladder", "arm_variant": "r3"}
    run = c.load_data(data, c.RunRecord)
    assert (run.agent.arm, run.agent.arm_variant) == ("modality-ladder", "r3")


def test_any_task_id_core_accepts():
    """R-147: a task id's form is its builder's; Core takes the v1 form and any other."""
    data = copy.deepcopy(EXAMPLES["task-set"][0])
    for task in ("dummy_aki@n20", "outside:risk/v2", "dummy_aki"):
        data["tasks"][0]["task"] = task
        assert c.load_data(data, c.TaskSet).tasks[0].task == task


def test_definitions_are_the_builders():
    """R-147 fix 1: Core stores a dataset's definitions untyped; the v1 builder checks them."""
    data = copy.deepcopy(EXAMPLES["dataset-config"][0]) | {"definitions": {"adult": {"any_form": "a builder's"}}}
    assert c.load_data(data, c.DatasetConfig).definitions["adult"] == {"any_form": "a builder's"}
