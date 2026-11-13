"""Studio's contracts (R-147): valid files load as frozen objects; wrong files are refused with the field named; Studio's
schemas match its models. The same checks as Core's, over Studio's own list."""
import copy
import json

import jsonschema
import pytest
from pydantic import ValidationError

from medomni.core import contracts as c
from medomni.studio import schemas

from .contract_examples import EXAMPLES

BY_FILE = {s.file: s for s in schemas.schemas()}


def test_studio_lists_its_contracts():
    assert {s.contract for s in schemas.schemas()} == {"dataset config", "recipe", "task template", "task proposal"}
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


def test_schemas_are_current():
    rendered = schemas.render()
    on_disk = {p.name: p.read_text(encoding="utf-8") for p in schemas.HERE.glob("*.schema.json")}
    assert rendered == on_disk, "run: python -m medomni.studio.schemas"


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


def refused(name, change, match):
    data = copy.deepcopy(EXAMPLES[name][0])
    change(data)
    with pytest.raises(c.ContractError, match=match):
        c.load_data(data, BY_FILE[name].model, name)


def test_rules_inside_contracts():
    refused("task-template", lambda d: d.update(template_id="other_aki"), "does not start with its dataset")
    refused("task-template", lambda d: d.update(evidence=["full"]), "includes default")
    refused("task-template", lambda d: d["targets"][0].update(metric="f1"), "metric")
    refused("recipe", lambda d: d.update(version=1.0), "version")  # a YAML float would turn 1.10 into 1.1
    refused("recipe", lambda d: d.update(version="1"), "version")
    refused("recipe", lambda d: d["require"][0].update({"from": "yesterday"}), "not a time")
    refused("recipe-labels", lambda d: d["aki"].pop("to"), "from and to")
    refused("recipe-labels", lambda d: d["aki"].update(value="LAB//x"), "exactly one")
    refused("v1-dataset-config", lambda d: d.update(definitions={"adult": {"not_a_requirement": 1}}), "definitions")


def test_v1_task_ids():
    """R-147 fix 4: the v1 builder checks its own id form; Core does not."""
    from medomni.studio.build.pool import BuildError, parse

    assert parse("dummy-mimic_aki@n4") == ("dummy-mimic_aki", "default", "n4")
    assert parse("dummy-mimic_aki:full@n4") == ("dummy-mimic_aki", "full", "n4")
    for bad in ("dummy-mimic_aki", "aki@n4", "outside:risk/v2"):
        with pytest.raises(BuildError, match="template>@<cohort"):
            parse(bad)
