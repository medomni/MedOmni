"""Build on dummy datasets: content, arms, ladder masks, config hash and refusals (part 3). No real data."""
import json
from pathlib import Path

import pytest

from medomni.studio import build as b
import importlib

from medomni.studio.build import checks
from medomni.core import workspace
from medomni.core.families.dummy.datasets import make_dataset

pool_mod = importlib.import_module("medomni.studio.build.pool")
REPO = Path(__file__).resolve().parents[2]
PAIR = "aireadi_crp-white-cell-count@n20"
LADDER = "aireadi_crp-white-cell-count@ladder"


@pytest.fixture(scope="module")
def ws(tmp_path_factory):
    root = tmp_path_factory.mktemp("build")
    copy = make_dataset(REPO / "studio/datasets/aireadi", root / "aireadi", subjects=30)
    cfg = root / "workspace.yaml"
    cfg.write_text(f"datasets: {{aireadi: {{path: {copy.root}}}}}\ncache: {root}/cache\ntasks: {root}/tasks\nruns: {root}/runs\n"
                   f"results: {root}/results.jsonl\nkeys_file: {root}/keys.env\nhf_cache: {root}/hf\n")
    return workspace.load(cfg)


def pick(result):
    return sorted(result.patients)[:12]


@pytest.fixture(scope="module", autouse=True)
def relaxed():
    mp = pytest.MonkeyPatch()
    mp.setattr(checks, "MIN_PER_CLASS", 1)
    # dummy copies plant no value for most labels: answers come from the subject id, so classes exist
    mp.setattr(pool_mod, "label", lambda rule, ctx, hooks=None: int(ctx.events[0]["subject_id"][-1]) % 2)
    yield
    mp.undo()


@pytest.fixture(scope="module")
def built(ws):
    return b.build([PAIR], ["encoders", "no-perception"], ws=ws, draw_with=pick)[0], Path(ws.tasks) / "atomtasks"


def atoms(tree, arm):
    return sorted(p for p in (tree / arm).iterdir() if p.is_dir())


def test_content_is_one_tree_and_arms_render_from_it(built):
    folder, tree = built
    assert folder == tree / "_content" / PAIR
    assert len(json.loads((folder / "content.json").read_text())["atoms"]) == 12
    assert len(atoms(tree, "encoders")) == 12 and len(atoms(tree, "no-perception")) == 12


def test_no_rendered_atom_holds_an_answer(built):
    _, tree = built
    for arm in ("encoders", "no-perception"):
        for a in atoms(tree, arm):
            assert not [p for p in a.rglob("*") if p.name in ("answers.csv", "gold.csv", "content.json")]


def test_arms_differ_only_in_the_perception_parts(built):
    _, tree = built
    a, n = atoms(tree, "encoders")[0], atoms(tree, "no-perception")[0]
    assert (a / "data/encoder_manifest.md").exists() and not (n / "data/encoder_manifest.md").exists()
    assert "perception" in (a / "environment/docker-compose.yaml").read_text()
    assert "perception:" not in (n / "environment/docker-compose.yaml").read_text()
    assert (a / "data/demographics.json").read_bytes() == (n / "data/demographics.json").read_bytes()
    assert (a / "instruction.md").read_text() != (n / "instruction.md").read_text()


def test_config_hash_per_arm_and_the_data_is_not_in_it(built):
    folder, _ = built
    m = json.loads((folder / "manifest.json").read_text())
    h = m["config_hash"]
    assert set(h) == {"encoders", "no-perception"} and h["encoders"] != h["no-perception"]
    assert all(v.startswith("cfg1:") for v in h.values())
    assert list(m["counts"]) == ["source population", "prediction time", "requirements", "labels", "file check"]


def test_a_changed_config_file_changes_the_hash(built, tmp_path):
    pair = pool_mod.load_pair(PAIR)
    arms = [b._arm("encoders")]
    before = b.config_hashes(pair, arms)["encoders"]
    f = tmp_path / "labels.yaml"
    f.write_text(pair.package.joinpath("labels.yaml").read_text() + "# changed\n")
    changed = type(pair)(**{**pair.__dict__, "package": pair.package})
    orig = changed.config_files
    assert before.startswith("cfg1:") and orig()
    files = dict(pair.config_files())
    files[next(k for k in files if k.endswith("labels.yaml"))] = f
    from medomni import __version__
    from medomni.core import hashing

    other = hashing.config_hash({**files, **arms[0].definition(pair, None)}, dataset_release=pair.config.description.version, medomni_release=__version__)
    assert other != before


def test_ladder_masks_its_rungs_and_shares_one_content_tree(ws):
    folder = b.build([LADDER], ["modality-ladder"], ws=ws, draw_with=pick)[0]
    tree = Path(ws.tasks) / "atomtasks/modality-ladder"
    assert sorted(p.name for p in tree.iterdir()) == ["r1", "r2", "r3", "r4", "r5", "r6"]
    r1 = sorted(p for p in (tree / "r1").iterdir())[0]
    r6 = tree / "r6" / r1.name
    inv = lambda p: set(json.loads((p / "data/inventory.json").read_text())["families"])  # noqa: E731
    assert inv(r1) <= inv(r6) and len(inv(r1)) < len(inv(r6))
    assert not (r1 / "data/tables/measurements.jsonl").exists() and (r1 / "data/demographics.json").exists()
    m = json.loads((folder / "manifest.json").read_text())["config_hash"]
    assert len(set(m.values())) == 6


def test_the_full_variant_is_refused():
    with pytest.raises(pool_mod.BuildError, match="not built"):
        pool_mod.load_pair("aireadi_crp-white-cell-count:full@n20")


def test_too_few_patients_in_a_class_stops_the_draw(ws):
    pair = pool_mod.load_pair(PAIR)
    p = pool_mod.Patient("1", type("C", (), {"anchor": None})(), {t.name: 1 for t in pair.template.targets}, {})
    r = pool_mod.Pool(pair, {"1": p}, {})
    with pytest.raises(pool_mod.BuildError, match="select"):
        pool_mod.draw(r)


def test_draw_is_nested_and_stable():
    pair = pool_mod.load_pair(PAIR)
    patients = {str(i): pool_mod.Patient(str(i), type("C", (), {"anchor": None})(), {"hs_crp_ge_3": i % 2, "wbc_value": 1.0}, {}) for i in range(60)}
    small = pool_mod.draw(pool_mod.Pool(pair, dict(patients), {}))
    big_pair = type(pair)(**{**pair.__dict__, "cohort": pair.cohort.model_copy(update={"select": pair.cohort.select.model_copy(update={"n": 50})})})
    big = pool_mod.draw(pool_mod.Pool(big_pair, dict(patients), {}))
    assert set(small) <= set(big)
