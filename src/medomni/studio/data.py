"""`medomni studio data`: check your copy of a dataset against its package (the v1 builder's input), write a new package.

`check` names each problem and exits 1 (Connect your data guide):

- the package: every file against its contract, and the checks across files (`core.recipes`);
- its dummy data: a dummy copy is written and loaded;
- your copy: its version, the files the package lists, the columns the readers need, and each hook's own problems,
  such as a raw label the label vocabulary does not classify (R-119, R-125).

The copy check never loads the dataset: `medomni cache build` does that.
"""
from __future__ import annotations

import csv
import re
import sys
import tempfile
from pathlib import Path

from medomni.core import workspace

CODES_COLUMNS = ["code", "description", "source_table"]


def _package_problems(package: Path) -> list[str]:
    from medomni.core.contracts import (Cohort, ContractError, DatasetConfig, DatasetPolicy, EvidenceRules,
                                        LabelLibrary, TaskTemplate, load)
    from medomni.core.recipes import check_package

    out = []
    files = [("dataset.yaml", DatasetConfig), ("policy.yaml", DatasetPolicy), ("labels.yaml", LabelLibrary),
             ("evidence.yaml", EvidenceRules)]
    for name, model in files:
        if not (package / name).is_file():
            out.append(f"{name}: missing")
            continue
        try:
            load(package / name, model)
        except ContractError as e:
            out.append(f"{name}: {e}")
    codes = package / "codes.csv"
    if not codes.is_file():
        out.append("codes.csv: missing")
    else:
        with open(codes, newline="", encoding="utf-8") as f:
            if csv.DictReader(f).fieldnames != CODES_COLUMNS:
                out.append(f"codes.csv: columns must be {', '.join(CODES_COLUMNS)}")
    for tdir in sorted((package / "tasks").glob("*/")):
        for path, model in [(tdir / "template.yaml", TaskTemplate)] + [
                (c, Cohort) for c in sorted((tdir / "cohorts").glob("*.yaml")) if not c.name.endswith(".tests.yaml")]:
            try:
                load(path, model)
            except ContractError as e:
                out.append(f"{path.relative_to(package)}: {e}")
    return out or check_package(package)


def _dummy_problems(package: Path) -> list[str]:
    from medomni.core.families.dummy.datasets import DummyError, make_dataset
    from medomni.core.loading import LoadError, load

    with tempfile.TemporaryDirectory(prefix="medomni-data-check-") as tmp:
        try:
            d = make_dataset(package, Path(tmp) / "dummy", subjects=6)
            load(package, d.root, Path(tmp) / "out")
        except (DummyError, LoadError) as e:
            return [f"dummy data: {e}"]
    return []


def _copy_problems(package: Path, raw_root: Path) -> list[str]:
    from medomni.core.contracts import DatasetConfig, load
    from medomni.core.loading import LoadError, hooks, missing_columns, verify
    from medomni.core.loading.options import options

    config = load(package / "dataset.yaml", DatasetConfig)
    readers = [(r.reader, options(r)) for r in config.read]
    out = []
    try:
        verify(config, readers, raw_root, package)
    except LoadError as e:
        out.append(str(e))
    out += [f"missing column: {c}" for c in missing_columns(readers, raw_root)]
    for kind, o in readers:
        if kind == "hook":
            mod = hooks.module(package, o.hook)
            if hasattr(mod, "problems"):
                out += list(mod.problems(raw_root, dict(o.params)))
    return out


def check(dataset: str, stream=None) -> int:
    from medomni.core.loading import find_package

    stream = stream or sys.stdout
    try:
        package = find_package(dataset)
    except FileNotFoundError as e:
        print(e, file=stream)
        return 1
    problems = _package_problems(package)
    print(f"package: {'ok' if not problems else f'{len(problems)} problem(s)'}", file=stream)
    if not problems:
        dummy = _dummy_problems(package)
        print(f"dummy data: {'ok' if not dummy else 'failed'}", file=stream)
        problems += dummy
    try:
        raw = workspace.dataset_path(workspace.load(), dataset)
    except workspace.WorkspaceError as e:
        problems.append(f"{e}; run `medomni bench data connect {dataset} --path <dir>`")
    else:
        if not raw.is_dir():
            problems.append(f"your copy: {raw} is not a folder")
        elif not problems:
            copy = _copy_problems(package, raw)
            print(f"your copy: {'ok' if not copy else f'{len(copy)} problem(s)'}", file=stream)
            problems += copy
    for p in problems:
        print(f"  {p}", file=stream)
    return 1 if problems else 0


DATASET_YAML = """\
# A new dataset package: fill in every field (Datasets reference page). Then run `medomni bench data check {name}`.
description: {{unit: patient, time: datetime, version: "1"}}
units: {{table: patients, column: subject_id}}
source: all
read:
- reader: csv
  options:
    tables:
      patients:
        file: patients.csv
        subject: subject_id
        events:
        - {{code: AGE, value: age}}
"""
LABELS_YAML = """\
# The label library (Recipes reference page). Templates name a label as `{name}:<label>`.
age-ge65:
  value: AGE
  op: ">="
  x: 65
  from: any
  to: any
"""
EVIDENCE_YAML = """\
# Evidence rules (Recipes reference page): what an atom sees of each table, relative to its prediction time.
tables: {}
static: {}
files: {}
"""
POLICY_YAML = """\
# The dataset policy (Datasets reference page): fill it in from the data owner's agreement.
dataset: {name}
version: "1"
access: credentialed
license: {{id: <the license or data use agreement>, url: <its address>}}
publish: {{schema: deny, templates: deny, recipes: deny, id_lists: deny, labels: deny, per_record_derived: deny, samples: deny}}
routes: {{local: allow, cloud: deny}}
use: {{commercial: false}}
sources: [<where the policy was read from>]
"""


def new(dataset: str, stream=None) -> int:
    """Write a package to fill in, at `studio/datasets/<dataset>/` under the current repository."""
    from medomni.core import plugins

    stream = stream or sys.stdout
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", dataset):
        print(f"'{dataset}' is not a dataset id (lower case, digits, hyphens)", file=stream)
        return 1
    package = plugins.find_repo() / "studio/datasets" / dataset
    if package.exists():
        print(f"{package} already exists", file=stream)
        return 1
    (package / "tasks").mkdir(parents=True)
    (package / "dataset.yaml").write_text(DATASET_YAML.format(name=dataset), encoding="utf-8")
    (package / "labels.yaml").write_text(LABELS_YAML.format(name=dataset), encoding="utf-8")
    (package / "evidence.yaml").write_text(EVIDENCE_YAML, encoding="utf-8")
    (package / "policy.yaml").write_text(POLICY_YAML.format(name=dataset), encoding="utf-8")
    (package / "codes.csv").write_text("code,description,source_table\nAGE,Age in years,patients\n", encoding="utf-8")
    print(f"wrote {package}", file=stream)
    return 0
