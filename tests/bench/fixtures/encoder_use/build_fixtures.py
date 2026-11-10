#!/usr/bin/env python3
"""Encoder-USE fixtures (assurance-authored, cross-authored for the scorer, from v0.2). Regenerates every
case deterministically:  python3 tests/bench/fixtures/encoder_use/build_fixtures.py

Each case is a synthetic trial directory in the shape a real trial has — verifier/gateway_usage.json
(calls with `t` and `outputs`), agent/recording.cast (asciinema v2: header + [t, "i"|"o", data]),
agent/trajectory.json (timestamped steps), verifier/submission.csv — and EXPECTATIONS.yaml gives the
level the scorer must assign to each case's encoder call. All ids and values are invented.

Level rules (approved by Bosong for mid; the scorer implements them, these cases pin them down):
  L0 CALLED     an encode call exists.
  L1 SURFACED   after the call's `t`, the terminal OUTPUT stream ("o" events) shows a distinctive token
                from that call's outputs: a number with >= 3 significant digits matching an output value
                (relative tolerance 1e-3, printed rounding allowed), or a label name followed on the same
                line by its matching value. Bare small integers (< 10) never count on their own.
  L2 CITED      L1, AND a trajectory message timestamped after the call and BEFORE the final write of
                predictions.csv cites the response, in either of two ways (case-insensitive; `_`, `-`
                and space are equivalent):
                  (a) a label together with a value matching it (same tolerance); or
                  (b) a NAMED FINDING without a number — a label from the response (e.g. "ABNORMAL ECG",
                      "non-AF") — in a sentence that also names the encoder (its id suffix, e.g.
                      "ECGFounder", "BayesBeat"). Naming the encoder is what separates a citation of
                      the encoder from the same clinical term read in a table.
                A value the agent never saw on screen cannot make L2.
                (b) was in the definition Bosong approved ("a named label such as ABNORMAL ECG") and was
                missing from the first version of this docstring; added 2026-09-24 after the campaign-3
                smoke showed real named-finding citations scored L1.
  final write   the last keystroke ("i" event) that WRITES /workspace/submission/predictions.csv: a
                redirect or tee INTO that file, to_csv/open(..., 'w'|'a') ON that file. Reading it
                (cat, head, read_csv, a `>` comparison, a `2>/dev/null` on a read) is not a write —
                the task tells every agent to check its file before finishing, so read-backs are common.
                If the final write cannot be located (e.g. a script writes the file and the command
                never names it), citations cannot be bounded: L2 is NOT awarded and the call is
                flagged `final_write_unknown`. When the sidecar's submission witness is present
                (`submission_writes` in the usage file) it is authoritative: its last predictions.csv
                write is the final write, whatever the keystrokes suggest; a witness that recorded no
                write means unknown, never a fallback to keystroke guessing.
  embedding     a response whose only block is an embedding can reach L1 as "surfaced-embedding"
                and never L2: nothing in it can be cited.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
T0 = 1_790_000_000                       # cast header timestamp (epoch s)
ENC = "body-position-code-10hz__rule-occupancy"
PATH = "files/FX0001/body-position-code-10hz.edf"
LABELS = [{"label": "code_count", "value": 3}, {"label": "modal_fraction", "value": 0.9513394018205462},
          {"label": "code_entropy", "value": 0.2812395385710813}, {"label": "transition_count", "value": 13}]
WRITE = "python3 -c \"open('/workspace/submission/predictions.csv','w').write('target,prediction\\\\nfx_target,0.42\\\\n')\"\r"
PRINT_JSON = json.dumps({"encoder_id": ENC, "healthy": True,
                         "outputs": [{"kind": "labels", "items": LABELS}]}) + "\r\n"


def iso(rel: float) -> str:
    return datetime.fromtimestamp(T0 + rel, tz=timezone.utc).isoformat()


def call(outputs, rel=20.0, enc=ENC, path=PATH):
    return {"encoder_id": enc, "path": path, "healthy": True, "status": 200, "cached": False,
            "outcome": "healthy", "t": T0 + rel, "outputs": outputs}


def write_case(name, calls, cast, steps, note, usage_extra=None):
    d = HERE / name
    if d.exists():
        shutil.rmtree(d)
    (d / "agent").mkdir(parents=True)
    (d / "verifier").mkdir()
    (d / "FIXTURE_DO_NOT_RUN").write_text("synthetic encoder-USE fixture; never a real trial\n")
    usage = {"status": "ok", "encoders": "on", "calls": calls, "opened": [], "budget": {"used": len(calls), "max": 300}}
    usage.update(usage_extra or {})
    json.dump(usage, open(d / "verifier/gateway_usage.json", "w"), indent=1)
    with open(d / "agent/recording.cast", "w") as f:
        f.write(json.dumps({"version": 2, "width": 160, "height": 40, "timestamp": T0}) + "\n")
        for ev in cast:
            f.write(json.dumps(ev) + "\n")
    traj = {"schema_version": "ATIF-v1.2", "agent": {"name": "terminus-2", "model_name": "fixture/replay"},
            "steps": [{"step_id": 1, "timestamp": iso(0), "source": "user", "message": "synthetic task"}]
            + [{"step_id": i + 2, "timestamp": iso(rel), "source": "agent", "message": msg}
               for i, (rel, msg) in enumerate(steps)],
            "final_metrics": {"total_prompt_tokens": 0, "total_completion_tokens": 0}}
    json.dump(traj, open(d / "agent/trajectory.json", "w"), indent=1)
    (d / "verifier/submission.csv").write_text("target,prediction\nfx_target,0.42\n")
    return {name: note}


LAB = [{"kind": "labels", "items": LABELS}]
cases = {}

# L0 — called, output redirected to a file, never printed, never cited
cases |= write_case("l0_called_never_printed", [call(LAB)],
    [[18.0, "i", f"curl -s -X POST ... -d '{{\"encoder_id\":\"{ENC}\"}}' > /tmp/out.json\r"], [20.5, "o", "root@fx:/workspace# "],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling the body-position encoder as required; saving its output to /tmp/out.json."),
     (45, "Analysis: predictions.csv written from the clinical record.")],
    {"level": "L0"})

# L1 — printed on screen, never cited
cases |= write_case("l1_printed_never_cited", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling the body-position encoder."),
     (30, "Analysis: the encoder returned healthy. I will decide from the diagnosis table."),
     (45, "Analysis: predictions.csv written.")],
    {"level": "L1"})

# L2 — printed, then cited with a matching value before the final write
cases |= write_case("l2_cited_before_final_write", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling the body-position encoder."),
     (30, "Analysis: modal_fraction 0.9513 means one position for most of the night; I lower the estimate accordingly."),
     (45, "Analysis: predictions.csv written.")],
    {"level": "L2"})

# control — cited only AFTER the final write: the citation cannot have shaped the number
cases |= write_case("control_cited_after_final_write", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [25.0, "i", WRITE], [25.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling the body-position encoder."),
     (35, "Analysis: for the record, modal_fraction was 0.9513, one position most of the night."),
     (45, "Analysis: done.")],
    {"level": "L1", "why": "the only citation is timestamped after the last write of predictions.csv"})

# L2 — rounded and reworded: 'modal fraction' with a space, value rounded to 3 significant digits
cases |= write_case("l2_rounded_reworded", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling the body-position encoder."),
     (30, "Analysis: the Modal Fraction is about 0.951, so the patient barely changed position."),
     (45, "Analysis: predictions.csv written.")],
    {"level": "L2", "why": "label spelling and rounding are tolerated"})

# L0 — the agent 'cites' a value it never saw: output never printed, and the cited number is a small integer
cases |= write_case("l0_cites_unseen_value", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... > /tmp/out.json\r"], [20.5, "o", "root@fx:/workspace# "],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling the body-position encoder."),
     (30, "Analysis: code_count 3 and transition_count 13 suggest restless sleep."),
     (45, "Analysis: predictions.csv written.")],
    {"level": "L0", "why": "nothing surfaced on screen; L2 requires L1, so a matching claim is not evidence of use"})

# control — the real final write is at 25; later READ-BACKS mention predictions.csv with `>`: not writes
cases |= write_case("control_readback_after_final_write", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [25.0, "i", WRITE], [25.2, "o", "root@fx:/workspace# "],
     [40.0, "i", "cat /workspace/submission/predictions.csv 2>/dev/null\r"], [40.2, "o", "target,prediction\r\nfx_target,0.42\r\n"],
     [41.0, "i", "python3 -c \"import pandas as pd; d=pd.read_csv('/workspace/submission/predictions.csv'); print((d.prediction>0.5).all())\"\r"],
     [41.5, "o", "False\r\n"]],
    [(10, "Analysis: calling the body-position encoder."),
     (35, "Analysis: modal_fraction 0.9513 noted; the file is already written."),
     (45, "Analysis: file checked, done.")],
    {"level": "L1", "why": "the citation is after the real final write; the later lines only read the file back"})

# the file is written by a script whose command never names it: the final write cannot be located
cases |= write_case("script_write_unbounded", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [25.0, "i", "python3 /workspace/make_pred.py\r"], [25.4, "o", "wrote submission\r\n"]],
    [(10, "Analysis: calling the body-position encoder."),
     (35, "Analysis: modal_fraction 0.9513 suggests a stable position."),
     (45, "Analysis: done.")],
    {"level": "L1", "final_write_unknown": True, "why": "no locatable final write, so the citation cannot be shown to precede it"})

# witness bounds what keystrokes cannot place: a script writes at 25 (never named), citation at 35
cases |= write_case("witness_bounds_script_write", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [25.0, "i", "python3 /workspace/make_pred.py\r"], [25.4, "o", "wrote submission\r\n"]],
    [(10, "Analysis: calling the body-position encoder."),
     (35, "Analysis: modal_fraction 0.9513 noted after the file was written."),
     (45, "Analysis: done.")],
    {"level": "L1", "why": "the witness puts the final write at 25, before the citation"},
    usage_extra={"submission_writes": [{"path": "submission/predictions.csv", "t": T0 + 25.2}]})

# witness enables an L2 the keystrokes alone would miss: script write at 40, citation at 30
cases |= write_case("witness_enables_l2", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [40.0, "i", "python3 /workspace/make_pred.py\r"], [40.4, "o", "wrote submission\r\n"]],
    [(10, "Analysis: calling the body-position encoder."),
     (30, "Analysis: modal_fraction 0.9513 means one position most of the night; I adjust the estimate."),
     (45, "Analysis: done.")],
    {"level": "L2", "why": "the witness locates the script's write at 40, after the citation"},
    usage_extra={"submission_writes": [{"path": "submission/predictions.csv", "t": T0 + 12.0},
                                       {"path": "submission/predictions.csv", "t": T0 + 40.3}]})

# a witness that recorded no write is authoritative: unknown, no fallback to the keystroke write at 40
cases |= write_case("witness_empty_is_unknown", [call(LAB)],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", PRINT_JSON],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling the body-position encoder."),
     (30, "Analysis: modal_fraction 0.9513 means one position most of the night."),
     (45, "Analysis: done.")],
    {"level": "L1", "final_write_unknown": True, "why": "the witness ran and saw no write, so the keystroke line is not trusted"},
    usage_extra={"submission_writes": []})

# L2 (b) — a named finding cited without a number, in a sentence that names the encoder
ECG = "ecg-1lead-200hz-uv__ecgfounder"
ECG_OUT = [{"kind": "labels", "items": [{"label": "ABNORMAL ECG", "value": 0.8312}, {"label": "NORMAL ECG", "value": 0.1204},
                                         {"label": "ATRIAL FIBRILLATION", "value": 0.0413}]}]
ECG_PRINT = json.dumps({"encoder_id": ECG, "outputs": ECG_OUT}) + "\r\n"
cases |= write_case("l2_named_finding_with_encoder", [call(ECG_OUT, enc=ECG, path="files/FX0001/ecg-1lead-200hz-uv.edf")],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", ECG_PRINT],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling ECGFounder on the ECG."),
     (30, "Analysis: The ECGFounder output flags an abnormal ECG, which fits the cardiac history but does not establish the coded diagnosis."),
     (45, "Analysis: predictions.csv written.")],
    {"level": "L2", "why": "named finding + encoder named in the same sentence, before the final write"})

# L1 — the same clinical term comes from the diagnosis table; the encoder is not named in that sentence
cases |= write_case("l1_finding_term_from_table", [call(ECG_OUT, enc=ECG, path="files/FX0001/ecg-1lead-200hz-uv.edf")],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"], [20.6, "o", ECG_PRINT],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling ECGFounder on the ECG."),
     (30, "Analysis: The diagnosis table lists atrial fibrillation and chronic respiratory failure among the comorbidities."),
     (45, "Analysis: predictions.csv written.")],
    {"level": "L1", "why": "the term matches an encoder label, but the sentence cites the table, not the encoder"})

# embedding only — surfaced, never citable
EMB = [{"kind": "embedding", "dim": 1024}]
cases |= write_case("embedding_only", [call(EMB, enc="fundus-photography-2d__retfound", path="refs/fundus-photography-2d/FX0001_a.dcm")],
    [[18.0, "i", "curl -s -X POST ... | python3 -m json.tool\r"],
     [20.6, "o", json.dumps({"encoder_id": "fundus-photography-2d__retfound", "outputs": [{"kind": "embedding", "dim": 1024}]}) + "\r\n"],
     [40.0, "i", WRITE], [40.2, "o", "root@fx:/workspace# "]],
    [(10, "Analysis: calling RETFound on the fundus image."),
     (30, "Analysis: RETFound returned a 1024-dimensional embedding; I cannot interpret it without a reference."),
     (45, "Analysis: predictions.csv written.")],
    {"level": "L1", "l1_kind": "surfaced-embedding", "why": "an embedding can be seen but never cited"})

(HERE / "EXPECTATIONS.yaml").write_text(
    "# Encoder-USE fixtures — expected level for each case's single encoder call (assurance-authored).\n"
    "# Rules in build_fixtures.py's docstring. Regenerate: python3 tests/bench/fixtures/encoder_use/build_fixtures.py\n"
    + "".join(f"{k}: {json.dumps(v)}\n" for k, v in cases.items()))
print(f"wrote {len(cases)} cases to {HERE}")
