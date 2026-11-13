"""`medomni studio release-check` (s4 part 4): licences, publish rules and data provenance over the release tree."""
from pathlib import Path

import yaml

from medomni.perception.registry import build
from medomni.studio.review import release_check as rc

REPO = Path(__file__).resolve().parents[2]


def test_the_release_tree_passes():
    found = rc.problems(REPO, images=False)
    assert found == {k: [] for k in found}, found


def test_the_licence_label_is_the_one_the_build_sets():
    assert rc.LICENSE_LABEL == build.LICENSE_LABEL
    edir = REPO / "perception/encoders/cgm-5min-mgdl/pyagata"
    cmd = build.command(edir, REPO)
    lic = yaml.safe_load((edir / "card.yaml").read_text())["license"]
    assert cmd[cmd.index(f"{build.LICENSE_LABEL}={lic}") - 1] == "--label"


def _package(root, publish_recipes="allow"):
    pkg = root / "studio/datasets/demo"
    (pkg / "tasks/t/cohorts").mkdir(parents=True)
    policy = yaml.safe_load((REPO / "studio/datasets/mimic-iv/policy.yaml").read_text())
    policy["dataset"] = "demo"
    policy["publish"]["recipes"] = publish_recipes
    (pkg / "policy.yaml").write_text(yaml.safe_dump(policy))
    return ["studio/datasets/demo/policy.yaml", "studio/datasets/demo/tasks/t/cohorts/n20.yaml"]


def test_a_file_the_publish_rules_cannot_place_fails(tmp_path):
    files = _package(tmp_path) + ["studio/datasets/demo/tasks/t/subjects.csv"]
    assert rc.package_problems(tmp_path, files) == [
        "dataset demo: tasks/t/subjects.csv is not a schema, template or recipe file; the publish rules can't place it"]


def test_a_denied_kind_fails(tmp_path):
    files = _package(tmp_path, publish_recipes="deny")
    assert rc.package_problems(tmp_path, files) == ["dataset demo: tasks/t/cohorts/n20.yaml is a recipes file, and the policy says deny"]


def test_data_files_need_a_provenance_that_states_a_licence(tmp_path):
    for rel in ("a/testdata/input.edf", "b/testdata/input.dcm", "c/testdata/input.hea", "docs/assets/logo.png"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(b"x")
    (tmp_path / "b/testdata/PROVENANCE.md").write_text("# Fixture\nAuthored, no patient data.\n")
    (tmp_path / "c/PROVENANCE.md").write_text("# Fixture\nLicense: CC0 1.0.\n")  # the folder above counts
    files = ["a/testdata/input.edf", "b/testdata/input.dcm", "b/testdata/PROVENANCE.md", "c/testdata/input.hea",
             "docs/assets/logo.png"]
    assert rc.data_problems(tmp_path, files) == ["a/testdata: data files with no PROVENANCE file beside them",
                                                 "b/testdata: b/testdata/PROVENANCE.md states no licence"]


def test_an_image_with_no_licence_label_fails(tmp_path):
    edir = tmp_path / "perception/encoders/fam/enc"
    edir.mkdir(parents=True)
    (edir / "card.yaml").write_text("license: MIT\n")
    (edir / "adapter.py").write_text("")
    files = ["perception/encoders/fam/enc/card.yaml"]
    image = "ghcr.io/medomni/fam__enc:dev"
    assert rc.card_problems(tmp_path, files, lambda i: {}) == [
        f"fam__enc: {image} has no {rc.LICENSE_LABEL} label; rebuild it with `medomni perception check`"]
    assert rc.card_problems(tmp_path, files, lambda i: {rc.LICENSE_LABEL: "Apache-2.0"}) == [
        f"fam__enc: {image} is labelled 'Apache-2.0', the card says 'MIT'"]
    assert rc.card_problems(tmp_path, files, lambda i: None) == [
        f"fam__enc: {image} is not on this machine, so its licence label can't be read"]
    assert rc.card_problems(tmp_path, files, lambda i: {rc.LICENSE_LABEL: "MIT"}) == []
    assert rc.card_problems(tmp_path, files, None) == []  # images not read
