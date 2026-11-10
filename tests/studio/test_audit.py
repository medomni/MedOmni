"""The audit (T1 on a dummy workspace): one engine, the task-isolation cell reads Bench's `task check`, verdicts bind (R-114)."""
import json
import shutil
from pathlib import Path

from medomni.core import workspace
from medomni.core.cli import main
from medomni.studio.review import engine, matrix, verdicts
from medomni.studio.review.scope import Scope


def audit_dir():
    return workspace.home() / "studio" / "review" / "audit"


def _matrix():
    return json.loads((audit_dir() / "matrix.json").read_text())


def _items(asset="tasks"):
    return [json.loads(line) for line in (audit_dir() / f"records/{asset}.jsonl").read_text().splitlines()]


def outcome(cell, auditor, check):
    return _matrix()[cell]["auditors"][auditor]["checks"][check]["outcome"]


def test_audit_runs_and_writes_the_report(built, capsys):
    ws, pair = built
    code = main(["studio", "audit", "--only", "tasks,runs,data"])
    assert code in (0, 1)
    assert (audit_dir() / "REPORT.md").read_text().startswith("# MedOmni audit")
    assert (audit_dir() / "FINDINGS.md").exists()
    assert outcome("T-ISOL", "M", "T-ISOL.1") == "pass"
    assert outcome("T-ISOL", "M", "T-ISOL.2") == "pass"
    assert outcome("T-COMP", "M", "T-COMP.3") == "pass"
    assert outcome("R-COMP", "M", "R-COMP.1") in ("pass", "warn")
    assert outcome("R-CONF", "M", "R-CONF.1") == "pass"
    # an LLM or human half with no verdict is unassessed, never a pass
    assert _matrix()["T-CLIN"]["auditors"]["H"]["outcome"] == "unassessed"


def test_task_isolation_reads_benchs_task_check(built, monkeypatch):
    ws, pair = built
    import medomni.studio.build as b

    monkeypatch.setattr(b, "run_checks", lambda p, ws=None, arm_names=None: [f"no answer in the evidence: {pair}: table labs holds a guarded code"])
    main(["studio", "audit", "--only", "tasks"])
    assert any(i["check"] == "T-ISOL.2" and i["outcome"] == "fail" and i["source"] == "bench task check" for i in _items())
    assert outcome("T-ISOL", "M", "T-ISOL.2") == "fail"  # kept: it harms the main claim


def test_a_non_main_claim_failure_is_demoted():
    item = engine.Item("D-COMP.1", "M", "x", matrix.FAIL, "missing", "s")
    assert engine.apply_severity([item])[0].outcome == matrix.WARN
    assert engine.apply_severity([engine.Item("T-ISOL.2", "M", "x", matrix.FAIL, "leak", "s")])[0].outcome == matrix.FAIL


def test_masking_hides_subjects_and_atoms():
    m = engine.Masker()
    m.register("dummy_task__9900000001__n4", "9900000001")
    masked = m.mask("atom dummy_task__9900000001__n4 and subject 9900000001 and file p12345678_0001.hea")
    assert "9900000001" not in masked and "p12345678" not in masked
    assert masked.startswith("atom dummy_task#")


def _scope(ws, pair):
    return Scope(ws, [pair])


def _verdict(reviews, sub, check, instance, h, **kw):
    (reviews / sub).mkdir(parents=True, exist_ok=True)
    with open(reviews / sub / "v.jsonl", "a") as f:
        f.write(json.dumps({"check": check, "instance": instance, "hash": h, "outcome": "pass", "note": "n", "by": "x", **kw}) + "\n")


def _state(reviews, scope, check, aud, instance):
    return next(i.outcome for i in verdicts.items(reviews, matrix.cells(), scope) if i.check == check and i.auditor == aud and i.instance == instance)


def test_task_verdict_survives_an_arm_change_and_reverts_on_a_label_change(built, tmp_path, package):
    ws, pair = built
    scope = _scope(ws, pair)
    reviews = tmp_path / "reviews"
    from medomni.studio import common

    p = common.load_pair(pair)
    h = verdicts.task_binding(p)
    _verdict(reviews, "human", "T-CLIN.1", pair, h, signed_by="A Clinician")
    assert _state(reviews, scope, "T-CLIN.1", "H", pair) == "pass"
    # an arm file changes: the ladder's masks
    arms_dir = package / "tasks/dummy-mimic_aki/arms"
    arms_dir.mkdir(exist_ok=True)
    (arms_dir / "modality-ladder.yaml").write_text("rungs: {}\n")
    assert verdicts.task_binding(common.load_pair(pair)) == h
    assert _state(reviews, _scope(ws, pair), "T-CLIN.1", "H", pair) == "pass"
    shutil.rmtree(arms_dir)
    # a label changes
    labels = package / "labels.yaml"
    before = labels.read_text()
    labels.write_text(before.replace("Does the patient", "Does this patient"))
    try:
        assert verdicts.task_binding(common.load_pair(pair)) != h
        assert _state(reviews, _scope(ws, pair), "T-CLIN.1", "H", pair) == "unassessed"
    finally:
        labels.write_text(before)


def test_ladder_rungs_share_one_binding(built):
    ws, pair = built
    from medomni.studio import common

    a = common.load_pair(pair)
    b = common.load_pair(pair)
    assert verdicts.task_binding(a) == verdicts.task_binding(b)  # no arm or variant enters it


def test_encoder_verdict_reverts_after_a_card_change(tmp_path):
    src = Path(__file__).resolve().parents[2] / "perception/encoders/cgm-5min-mgdl/pyagata"
    edir = tmp_path / "family/enc"
    edir.mkdir(parents=True)
    shutil.copy(src / "card.yaml", edir / "card.yaml")
    card = {"runtime": {"digest": "sha256:abc"}}
    before = verdicts.encoder_binding(edir, card)
    (edir / "card.yaml").write_text((edir / "card.yaml").read_text() + "\n# changed\n")
    assert verdicts.encoder_binding(edir, card) != before


def test_unsigned_human_verdict_is_unassessed(built, tmp_path):
    ws, pair = built
    scope = _scope(ws, pair)
    from medomni.studio import common

    reviews = tmp_path / "reviews"
    _verdict(reviews, "human", "T-CLIN.1", pair, verdicts.task_binding(common.load_pair(pair)))
    assert _state(reviews, scope, "T-CLIN.1", "H", pair) == "unassessed"


def test_review_form_round_trip_binds_the_config_hash(built, tmp_path, capsys):
    ws, pair = built
    import yaml

    main(["studio", "review-form", pair])
    slug = pair.replace("@", "_")
    p = workspace.home() / "studio/review/review-form" / f"{slug}.yaml"
    form = yaml.safe_load(p.read_text())
    assert form["hash"].startswith("cfg1:")
    assert main(["studio", "review-form", pair, "--submit", str(p)]) == 2  # unsigned
    form["signed_by"] = "A Clinician"
    form["checks"]["T-CLIN.1"]["outcome"] = "pass"
    p.write_text(yaml.safe_dump(form, sort_keys=False))
    assert main(["studio", "review-form", pair, "--submit", str(p)]) == 0
    line = (workspace.home() / f"studio/review/audit/reviews/human/{slug}.jsonl").read_text().splitlines()[-1]
    assert json.loads(line)["hash"] == form["hash"]
    form["hash"] = "cfg1:" + "0" * 64
    p.write_text(yaml.safe_dump(form, sort_keys=False))
    assert main(["studio", "review-form", pair, "--submit", str(p)]) == 2


def test_family_cell_checks_samples(built, tmp_path):
    from medomni.core import families
    from medomni.core.families.dummy import make_dummy
    from medomni.studio.review.checks.families import run

    fid = "body-position-code-10hz"
    d = tmp_path / fid
    for i in range(3):
        make_dummy(families.get(fid), i, d, f"s-{i}", level="format")
    ws, pair = built
    scope = Scope(ws, [pair], tmp_path)
    scope.families = {fid: families.get(fid)}
    sink = engine.Sink(scope.mask)
    run(scope, sink)
    assert any(i.check == "F-CONF.1" and i.outcome == matrix.PASS for i in sink.items)


def test_no_project_imports_studio():
    src = Path(__file__).resolve().parents[2] / "src/medomni"
    for project in ("core", "bench", "perception"):
        for p in (src / project).rglob("*.py"):
            assert "medomni.studio" not in p.read_text(encoding="utf-8"), p
