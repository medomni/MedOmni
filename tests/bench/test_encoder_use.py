"""Encoder use (L0 called, L1 surfaced, L2 cited) against v0.2's cross-authored fixtures, and its place in a score row."""
import json
import shutil
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import yaml

from medomni.bench.scoring import encoder_use

FX = Path(__file__).parent / "fixtures/encoder_use"
EXPECT = yaml.safe_load((FX / "EXPECTATIONS.yaml").read_text())


@pytest.mark.parametrize("case", sorted(EXPECT))
def test_every_case_matches_expectation(case):
    want, got = EXPECT[case], encoder_use.levels(FX / case)
    assert len(got) == 1
    assert got[0]["level"] == want["level"]
    if "l1_kind" in want:
        assert got[0]["l1_kind"] == want["l1_kind"]
    if "final_write_unknown" in want:
        assert got[0]["final_write_unknown"] == want["final_write_unknown"]


READS = ["cat /workspace/submission/predictions.csv 2>/dev/null",
         "python3 -c \"import pandas as pd; d=pd.read_csv('/workspace/submission/predictions.csv'); print(d.prediction>0.5)\"",
         "head /workspace/submission/predictions.csv >&2",
         "wc -l /workspace/submission/predictions.csv"]
WRITES = ["echo 'target,prediction' > /workspace/submission/predictions.csv",
          "printf 'x,0.4\\n' >> /workspace/submission/predictions.csv",
          "python3 -c \"open('/workspace/submission/predictions.csv','w').write('a')\"",
          "df.to_csv('/workspace/submission/predictions.csv', index=False)",
          "cat out.csv | tee /workspace/submission/predictions.csv",
          "cp /tmp/p.csv /workspace/submission/predictions.csv"]


def test_reads_are_not_writes_and_writes_are():
    assert not any(encoder_use.WRITE.search(c) for c in READS)
    assert all(encoder_use.WRITE.search(c) for c in WRITES)


def test_the_witness_wins_and_an_empty_one_is_unknown():
    assert encoder_use.final_write([], {"submission_writes": [{"path": "predictions.csv", "t": 5.0}]}) == (5.0, "witness")
    assert encoder_use.final_write([], {"submission_writes": []}) == (None, "unknown")
    assert encoder_use.final_write([(1.0, "i", "cat predictions.csv")], {}) == (None, "unknown")


CASES = ["l0_called_never_printed", "l1_printed_never_cited", "l2_cited_before_final_write", "control_cited_after_final_write"]


def test_summary_over_fixture_atoms():
    calls = {c: encoder_use.levels(FX / c) for c in CASES} | {"silent": []}
    u = encoder_use.summary(calls, n_atoms=5)
    assert u["atoms_calling"] == 4 and u["atoms_n"] == 5
    assert u["share"] == {"L0": 1.0, "L1": 0.75, "L2": 0.25}
    assert u["share_all_atoms"] == {"L0": 0.8, "L1": 0.6, "L2": 0.2}
    assert u["l1_to_l2_drop"] == pytest.approx(2 / 3)
    assert u["answered_calls_without_outputs"] == 0 and "unmeasured" in u["L3"]
    assert encoder_use.summary({"x": calls[CASES[2]]}, 1, relevant={"cxr-radiograph-2d"})["atoms_calling"] == 0


def test_a_score_row_carries_the_cells_encoder_use(tmp_path, monkeypatch):
    """write_records grades a perception arm's trials into encoder_use.jsonl; score_run puts the summary on each row.
    A no-perception job writes no file, and its rows carry an empty encoder_use."""
    from medomni.bench import runs
    from medomni.bench.scoring import score_run

    content = tmp_path / "tree/_content/p"
    content.mkdir(parents=True)
    atoms = [{"atom": f"a{i}", "subject": f"s{i}"} for i in range(4)]
    (content / "content.json").write_text(json.dumps({"version": "1.0", "targets": [{"name": "y", "metric": "auc"}], "atoms": atoms}))
    (content / "answers.csv").write_text("subject_id,target,value,metric\n" + "".join(f"s{i},y,{int(i >= 2)},auc\n" for i in range(4)))
    (content / "manifest.json").write_text(json.dumps({"config_hash": {"encoders": "cfg1:" + "a" * 64, "no-perception": "cfg1:" + "b" * 64}}))
    for arm, max_calls in (("encoders", 10), ("no-perception", None)):
        folder = tmp_path / f"runs/job-{arm}"
        trials = []
        for i, case in enumerate(CASES):
            t = folder / f"a{i}"
            shutil.copytree(FX / case, t)
            (t / "verifier/submission.csv").write_text(f"target,prediction\ny,{0.2 + 0.2 * i}\n")
            trials.append(("p", f"a{i}", t, None, "m"))
        job = NS(folder=folder, tree=tmp_path / "tree", name=f"job-{arm}", set_name="medomni-bench/x", variant=None,
                 agent=NS(name="terminus-2-luna"), arm=NS(name=arm, max_calls=max_calls))
        runs.write_records(job, trials)
        rows = score_run(folder, tmp_path / "tree/_content", "c" * 64, tmp_path / "results.jsonl")
        assert [r["value"] for r in rows] == [1.0]
        if max_calls:
            assert rows[0]["encoder_use"]["share"] == {"L0": 1.0, "L1": 0.75, "L2": 0.25}
            first = json.loads((folder / "runs.jsonl").read_text().splitlines()[0])
            assert sum(first["agent"]["encoder_calls"].values()) == 1
        else:
            assert rows[0]["encoder_use"] == {} and not (folder / "encoder_use.jsonl").exists()
