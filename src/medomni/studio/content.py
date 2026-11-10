"""Studio's content kinds (R-145): the v1 builder's dataset packages, with their templates and cohorts (R-144)."""
from medomni.core.contracts import (Cohort, CohortTests, DatasetConfig, DatasetPolicy, EvidenceRules, LabelLibrary,
                                    TaskTemplate)
from medomni.core.plugins import Files, Kind

CONTENT = (
    Kind("datasets", "studio/datasets/*/dataset.yaml", 1),
    Kind("tasks", "studio/datasets/*/tasks/*/template.yaml", 1),
    Files("dataset config", "datasets", "studio/datasets/*/dataset.yaml", DatasetConfig),
    Files("dataset policy", "policies", "studio/datasets/*/policy.yaml", DatasetPolicy),
    Files("recipe", "recipes", "studio/datasets/*/labels.yaml", LabelLibrary),
    Files("recipe", "recipes", "studio/datasets/*/evidence.yaml", EvidenceRules),
    Files("task template", "templates", "studio/datasets/*/tasks/*/template.yaml", TaskTemplate),
    Files("recipe", "recipes", "studio/datasets/*/tasks/*/cohorts/*.tests.yaml", CohortTests),
    Files("recipe", "recipes", "studio/datasets/*/tasks/*/cohorts/*.yaml", Cohort, exclude=("*.tests.yaml",)),
)
