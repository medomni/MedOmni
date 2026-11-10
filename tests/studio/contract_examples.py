"""One valid instance per Studio contract schema (R-147), plus one required field to drop from each. Invented values only."""
from tests.core.contract_examples import EXAMPLES as CORE

EXAMPLES = {
    "v1-dataset-config": (CORE["dataset-config"][0] | {"definitions": {"adult": {"any": ["^AGE//"]}}}, CORE["dataset-config"][1]),
    "recipe": ({"version": "1.0", "source": {"fraction": 0.05}, "anchor": {"event": "ADMISSION", "pick": "first", "plus": "24 hours"},
                "require": [{"any": ["^DIAGNOSIS//ICD//(N17|584)"], "from": "anchor - 24 hours", "to": "anchor"},
                            {"files": ["cxr-radiograph-2d"], "same_visit": True},
                            {"has_label": "aki"}, {"definition": "adult"}],
                "select": {"n": 20, "by": ["aki"], "seed": 7}}, "select"),
    "recipe-tests": ({"patients": [{"events": [{"subject_id": "DUMMY-1", "code": "ADMISSION"}],
                                    "expect": {"in": False}}]}, "patients"),
    "recipe-labels": ({"aki": {"exists": "^DIAGNOSIS//ICD//N17", "from": "anchor", "to": "anchor + 7 days",
                               "guard": {"codes": ["^DIAGNOSIS//ICD//N17"]}},
                       "creat_high": {"value": "LAB//creatinine", "pick": "max", "op": ">=", "x": 1.5,
                                      "from": "anchor", "to": "any"}}, None),
    "recipe-evidence": ({"tables": {"labevents": {"time": "charttime", "write_empty": True}},
                         "static": {"blank": ["dod"]}, "files": {}}, None),
    "task-template": ({"template_id": "dummy_aki", "dataset": "dummy",
                       "authors": [{"name": "A. Contributor"}],
                       "targets": [{"name": "aki", "label": "dummy:aki", "metric": "auc"}],
                       "input": {"tables": ["labevents"]}, "evidence": ["default", "full"],
                       "agent": {"statement": "Predict acute kidney injury.", "instruction": "Predict {{ targets }}.",
                                 "environment": {"cpus": 2, "memory_mb": 4096, "allow_internet": True,
                                                 "agent_timeout_sec": 1200, "verifier_timeout_sec": 300},
                                 "submission_path": "/workspace/submission/predictions.csv"}}, "targets"),
    "task-proposal": ({"title": "Early AKI", "by": "A. Clinician", "at": "2026-09-06", "mode": "targeted",
                       "state": "draft"}, "state"),
}
