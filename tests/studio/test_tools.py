"""Studio on a dummy dataset (T1): every tool loads through its kind's interface and every command runs."""
import json
from pathlib import Path

from medomni.core import workspace
from medomni.core.cli import main
from medomni.studio import tools

REPO = Path(__file__).resolve().parents[2]


def studio(*args):
    return main(["studio", *args])


def written(kind, name):
    return workspace.home() / "studio" / kind / name


def test_every_tool_loads_and_follows_its_kind():
    found = tools.found()
    assert not found.errors
    kinds = set()
    for name, target in found.targets.items():
        tool = tools.load(target, name)
        assert tools.problems(tool, name) == [], name
        kinds.add(tool.kind)
    assert kinds == set(tools.KINDS)


def test_check_command_passes_and_names_unknown_tools(capsys):
    assert studio("check", "survey") == 0
    assert "ok" in capsys.readouterr().out
    assert studio("check", "no-such-tool") == 1


def test_survey(built, capsys):
    assert studio("survey", "dummy-mimic") == 0
    doc = json.loads((written("survey", "survey") / "dummy-mimic.json").read_text())
    assert doc["subjects"] == 40 and doc["codes"] and doc["families"]
    assert any(c["pair"] == "dummy-mimic_aki@n10" for c in doc["cohorts"])
    assert "dummy-mimic" in capsys.readouterr().out


def test_census(built, capsys):
    ws, pair = built
    assert studio("census", pair) == 0
    doc = json.loads((written("survey", "census") / f"{pair.replace('@', '_')}.json").read_text())
    assert set(doc[pair]["families"]) == {"encoders", "no-perception"}
    assert "aki" in doc[pair]["answers"]


def test_intake_and_freeze(tmp_path, capsys):
    csv_path = tmp_path / "proposals.csv"
    csv_path.write_text("received_at,name,institution,dataset,task_name,statement,mode,targets,streams\n"
                        "2150-01-01,A Person,Hospital,mimic,Predict heart failure from ECG,Does it?,targeted,HF | Death,12-lead diagnostic ECG\n")
    assert studio("intake", str(csv_path)) == 0
    out = written("propose", "intake")
    tid = "mimic-iv_hf-ecg"
    import yaml

    p = yaml.safe_load((out / f"{tid}.yaml").read_text())
    assert p["state"] == "draft" and p["draft"]["unresolved"]
    assert (out / "MANIFEST.md").exists() and (out / f"{tid}.md").exists()
    assert studio("intake", str(out / f"{tid}.yaml")) == 2  # a draft is refused
    p["state"] = "signed-off"
    p["draft"].pop("unresolved")
    p["draft"]["template"] = yaml.safe_load((REPO / "src/medomni/studio/testing/datasets/dummy-mimic/tasks/dummy-mimic_aki/template.yaml").read_text())
    p["draft"]["cohort"] = yaml.safe_load((REPO / "src/medomni/studio/testing/datasets/dummy-mimic/tasks/dummy-mimic_aki/cohorts/n4.yaml").read_text())
    signed = tmp_path / "signed.yaml"
    signed.write_text(yaml.safe_dump(p, sort_keys=False))
    assert studio("intake", str(signed)) == 0
    assert (written("propose", "intake") / "dummy-mimic_aki/template.yaml").exists()
    assert (written("propose", "intake") / "dummy-mimic_aki/cohorts/n20.yaml").exists()


def test_relevance_with_and_without_a_proposal(tmp_path):
    import yaml

    assert studio("relevance", "dummy-mimic_aki") == 0
    doc = yaml.safe_load((written("propose", "relevance") / "dummy-mimic_aki.yaml").read_text())
    assert "clinical-record-table" in doc["dummy-mimic_aki"]["declared"]
    csv_path = tmp_path / "p.csv"
    csv_path.write_text("received_at,name,institution,dataset,task_name,statement,mode,targets,streams\n"
                        "1,A,B,aireadi,Predict depression from lifestyle,s,m,T,CES-D-10 depression score | Technologist sleep staging | HbA1c\n")
    assert studio("relevance", "aireadi_depression-lifestyle", "--proposals", str(csv_path)) == 0
    t = yaml.safe_load((written("propose", "relevance") / "aireadi_depression-lifestyle.yaml").read_text())["aireadi_depression-lifestyle"]
    assert "clinical-record-table" in t["declared"] and "clinical-measurement-irregular" in t["declared"]


def test_preview_and_download_list(built, capsys):
    ws, pair = built
    assert studio("preview", pair) == 0
    out = capsys.readouterr().out
    assert "source population" in out and "per class" in out
    doc = json.loads((written("preview", "preview") / f"{pair.replace('@', '_')}.json").read_text())
    assert doc["counts"]["source population"] == 40


def test_download_list_bdsp_hook(t1_guard, tmp_path, monkeypatch, capsys):
    from medomni.studio.dummy import make as make_dataset

    ws_dir = workspace.home()
    copy = make_dataset(REPO / "studio/datasets/bdsp", tmp_path / "bdsp", subjects=80)
    cfg = workspace.load()
    text = (ws_dir / "workspace.yaml").read_text() if (ws_dir / "workspace.yaml").exists() else ""
    assert cfg is not None
    (ws_dir / "workspace.yaml").write_text(text.replace("datasets: {", f"datasets: {{bdsp: {{path: {copy.root}}}, ", 1))
    assert studio("download-list", "bdsp") == 0
    rows = [line.split("\t") for line in (written("preview", "download-list") / "bdsp.txt").read_text().splitlines()]
    assert all(len(r) == 3 and r[2] in ("file", "folder") for r in rows)
    nights = [r for r in rows if not r[1].startswith("_index/")]
    assert len(rows) - len(nights) == 3 and nights and len(nights) % 3 == 0
    assert all(k.startswith("PSG/bids/I0006/") and p.endswith((".h5", "_scores.csv", "_events.csv")) for k, p, _ in nights)


def test_download_hooks_vitaldb_and_mimic(tmp_path):
    """Both hooks list the index first, then one entry set per source patient, paths in the package's own layout."""
    from medomni.core.loading import find_package, hooks

    v = hooks.module(find_package("vitaldb"), "download", derives=False)
    assert [e[2] for e in v.index_files()] == ["gunzip"] * 3
    assert v.files(tmp_path, {}, {"12": {}, "3": {}}) == [
        ("https://api.vitaldb.net/3.vital", "cases/3.vital", "file"), ("https://api.vitaldb.net/12.vital", "cases/12.vital", "file")]
    m = hooks.module(find_package("mimic-iv"), "download", derives=False)
    for rel, line in [("cxr/IMAGE_FILENAMES", "files/p10/p10000032/s1/a.jpg\nfiles/p11/p11000001/s2/b.jpg"),
                      ("ecg/record_list.csv", "subject_id,path\n10000032,files/p1000/p10000032/s3/3\n11000001,files/p1100/p11000001/s4/4"),
                      ("wdb/RECORDS", "waves/p100/p10000032/1/\n")]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(line + "\n")
    got = m.files(tmp_path, {}, {"10000032": {}})
    assert [p for _, p, _ in got] == ["cxr/files/p10/p10000032/s1/a.jpg", "ecg/files/p1000/p10000032/s3/3.hea",
                                      "ecg/files/p1000/p10000032/s3/3.dat", "wdb/waves/p100/p10000032/1/"]
    assert got[-1][2] == "folder" and all(s.startswith("https://physionet.org/files/") for s, _, _ in got)


def test_build_sheet(built):
    ws, pair = built
    assert studio("build-sheet", pair) == 0
    text = (written("report", "build-sheet") / f"{pair.replace('@', '_')}.md").read_text()
    assert pair in text and "encoders" in text and "cfg1:" in text


def test_tables(built, capsys):
    assert studio("tables") == 0
    out = capsys.readouterr().out
    assert "0.750" in out and "aki" in out


def test_progress_and_bench_health(built, capsys):
    assert studio("progress", "run-1") == 0
    out = capsys.readouterr().out
    assert "1/1" in out and "TOTAL" in out
    assert studio("bench-health", "run-1") == 0
    out = capsys.readouterr().out
    assert "e__one" in out and "PASS" in out and "FAIL" in out  # e__two crashed


def test_diagrams(tmp_path):
    assert studio("diagrams", str(REPO / "docs/assets/diagrams.yaml"), "--out", str(tmp_path / "d")) == 0
    assert list((tmp_path / "d").glob("*.drawio.svg"))


def test_unknown_run_is_named(built, capsys):
    assert studio("progress", "nope") == 2
    assert "no run" in capsys.readouterr().err


def test_encoder_status(capsys):
    assert studio("encoder-status") == 0
    out = capsys.readouterr().out
    assert "built" in out


def test_encoder_demo_local(capsys):
    assert studio("encoder-demo", "body-position-code-10hz__rule-occupancy", "--local") == 0
    out = capsys.readouterr().out
    assert "healthy True" in out and "modality" in out


def test_testdata_writes_conforming_inputs(tmp_path):
    from medomni.core import families
    from medomni.core.families.check import conforms

    out = tmp_path / "td"
    assert studio("testdata", "body-position-code-10hz__rule-occupancy", "--out", str(out)) == 0
    assert (out / "PROVENANCE.md").exists() and (out / "input-empty.edf").read_bytes() == b""
    assert conforms(families.get("body-position-code-10hz"), out / "input.edf") == []
    assert studio("testdata", "body-position-code-10hz__rule-occupancy", "--out", str(out)) == 1  # already has inputs


def test_family_samples(built, tmp_path, capsys):
    from medomni.core import families
    from medomni.core.families.check import conforms

    out = tmp_path / "samples"
    assert studio("family-samples", "cxr-radiograph-2d", "--dataset", "dummy-mimic", "-n", "2", "--out", str(out)) == 0
    files = [f for f in out.iterdir() if f.name != "PROVENANCE.json"]
    assert len(files) == 2
    assert all(conforms(families.get("cxr-radiograph-2d"), f) == [] for f in files)
    assert len(json.loads((out / "PROVENANCE.json").read_text())) == 2
