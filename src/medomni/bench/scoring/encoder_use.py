"""Encoder use: how far an agent took each encoder answer (v0.2's levels, approved by Bosong 2026-09-24).

  L0 CALLED    an encode call was answered (the perception service's call log, `t` = call time).
  L1 SURFACED  after the call, the terminal output shows a distinctive token from that call's outputs: a number with
               3 or more significant digits matching an output value (relative tolerance 1e-3, printed rounding
               allowed), or a label followed on the same line by its value. A bare integer under 10 never counts
               on its own. An embedding-only answer surfaces as `surfaced-embedding`.
  L2 CITED     L1, and an agent message after the call and before the final write of predictions.csv cites the
               answer (case-insensitive; `_`, `-` and space alike): a label with its value, or a named finding
               (a label from the answer) in a sentence that also names the encoder (its id suffix). A value never
               seen on screen can't make L2.
  final write  the service's submission witness (`submission_writes`) when it ran; otherwise the last keystroke
               that writes into predictions.csv, never a read-back. When neither locates it, L2 isn't awarded and
               the call is flagged `final_write_unknown`.

L3 (influence) needs a paired ablation, so it is reported as unmeasured. Known limits, reported, not corrected: a value
several calls share surfaces for all of them; lab summaries are also readable from measurements.jsonl, so their L1 is
marked `ambiguous-source`.

The levels read a trial folder in Harbor's layout: `verifier/gateway_usage.json`, `agent/recording.cast` (asciinema
v2) and `agent/trajectory.json`. The fixtures in `tests/bench/fixtures/encoder_use/` pin every rule.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")
NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
P = r"""['"]?[^\s'";|&>]*predictions\.csv"""
WRITE = re.compile("|".join([
    r"(?<![0-9&])>>?(?!&)\s*" + P,                                   # a redirect into the file (not 2>, >&)
    r"\btee\s+(?:-a\s+)?" + P,                                      # tee into it
    r"\b(?:cp|mv)\s+\S+\s+" + P,                                    # a copy or move onto it
    r"""to_csv\(\s*['"][^'"]*predictions\.csv""",                    # pandas
    r"""open\(\s*['"][^'"]*predictions\.csv['"]\s*,\s*['"][wa]""",  # open for writing
]))
AMBIGUOUS_FAMILIES = {"clinical-measurement-irregular"}  # the same values are readable from measurements.jsonl
SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")
RANK = {"L0": 0, "L1": 1, "L2": 2}
LEVELS = ("L0", "L1", "L2")


def _norm(s: str) -> str:
    return re.sub(r"[\s_\-]+", " ", str(s).lower()).strip()


def _alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _sig(tok: str) -> int:
    return len(re.sub(r"[eE].*$", "", tok).replace("-", "").replace(".", "").lstrip("0"))


def _matches(tok: str, v) -> bool:
    """Token `tok` shows value v: within 1e-3 relative, or v rounded to tok's decimals."""
    try:
        x, v = float(tok), float(v)
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(x) and math.isfinite(v)):
        return False
    if abs(x - v) <= 1e-3 * max(abs(v), 1e-12):
        return True
    dec = len(tok.split(".")[1]) if "." in tok and "e" not in tok.lower() else 0
    return dec > 0 and abs(x - v) <= 0.5 * 10 ** (-dec) + 1e-12


def offered(outputs: list) -> tuple[list[tuple[str | None, float]], bool]:
    """The (label, value) pairs an answer offered, and whether it was embedding-only."""
    out: list = []
    kinds = {b.get("kind") for b in outputs or []}
    for b in outputs or []:
        if b.get("kind") == "labels":
            out += [(i.get("label"), i.get("value")) for i in b.get("items") or [] if isinstance(i.get("value"), (int, float))]
        elif b.get("kind") == "events":
            out += list((b.get("label_counts") or {}).items())
        elif b.get("kind") == "embedding" and b.get("dim"):
            out.append(("embedding", b["dim"]))
        elif b.get("kind") == "text":
            out += [(None, float(t)) for t in NUM.findall(b.get("text") or "") if _sig(t) >= 3]
    return out, kinds == {"embedding"}


def surfaced(screen: list[str], pairs: list[tuple[str | None, float]]) -> bool:
    for line in screen:
        toks, nline = NUM.findall(line), _norm(line)
        for label, v in pairs:
            for tok in toks:
                if not _matches(tok, v):
                    continue
                if label and _norm(label) in nline:
                    return True  # a label and its value on one line (small integers allowed)
                if _sig(tok) >= 3 and not (abs(float(tok)) < 10 and float(tok).is_integer()):
                    return True  # a distinctive number on its own
    return False


def cited(message: str, pairs: list[tuple[str | None, float]], encoder_id: str | None = None) -> bool:
    nmsg, toks = _norm(message), NUM.findall(message)
    if any(label and _norm(label) in nmsg and any(_matches(t, v) for t in toks) for label, v in pairs):
        return True  # a label with a matching value
    suffix = _alnum((encoder_id or "").split("__")[-1])
    if not suffix:
        return False
    labels = {_norm(label) for label, _ in pairs if label and label != "embedding"}
    for sent in SENTENCE.split(message):  # a named finding and the encoder, in one sentence
        if suffix in _alnum(sent):
            ns = f" {_norm(re.sub(r'[^A-Za-z0-9_-]+', ' ', sent))} "
            if any(f" {lab} " in ns for lab in labels):
                return True
    return False


def load_cast(path: Path) -> list[tuple[float, str, str]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return []
    t0 = float(json.loads(lines[0]).get("timestamp") or 0)
    events = []
    for line in lines[1:]:
        try:
            t, kind, data = json.loads(line)
            events.append((t0 + float(t), kind, data))
        except (ValueError, TypeError):
            pass
    return events


def final_write(events, usage: dict) -> tuple[float | None, str]:
    """(time, source): the witness's last write when it ran, else the last keystroke writing into predictions.csv,
    else (None, "unknown"). A witness that saw no write means unknown, never a fallback to keystrokes."""
    if "submission_writes" in usage:
        ts = [float(w["t"]) for w in usage["submission_writes"] if str(w.get("path", "")).endswith("predictions.csv")]
        return (max(ts), "witness") if ts else (None, "unknown")
    ts = [t for t, k, d in events if k == "i" and WRITE.search(d)]
    return (max(ts), "keystroke") if ts else (None, "unknown")


def _ts(s: str) -> float:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def levels(trial: Path) -> list[dict]:
    """One record per answered encode call: {encoder_id, level, l1_kind, final_write, final_write_unknown}. An answered
    call with no outputs has level None (`declared` when it was a card-backed refusal)."""
    trial = Path(trial)
    usage = json.loads((trial / "verifier/gateway_usage.json").read_text(encoding="utf-8"))
    cast, traj = trial / "agent/recording.cast", trial / "agent/trajectory.json"
    events = load_cast(cast) if cast.is_file() else []
    fw, fw_source = final_write(events, usage)
    steps = json.loads(traj.read_text(encoding="utf-8")).get("steps", []) if traj.is_file() else []
    msgs = [(_ts(s["timestamp"]), str(s.get("message") or "")) for s in steps if s.get("source") == "agent" and s.get("timestamp")]
    out = []
    for c in usage.get("calls") or []:
        if c.get("status") not in (200, None):
            continue
        rec = {"encoder_id": c.get("encoder_id"), "level": None, "l1_kind": None, "final_write": fw_source,
               "final_write_unknown": fw is None, "declared": c.get("outcome") == "declared"}
        if not c.get("outputs"):
            out.append(rec)
            continue
        ct = float(c.get("t") or 0)
        pairs, emb_only = offered(c["outputs"])
        screen = [line for et, k, d in events if k == "o" and et >= ct for line in ANSI.sub("", d).replace("\r", "").split("\n")]
        rec["level"] = "L0"
        if surfaced(screen, pairs):
            rec["level"] = "L1"
            family = (c.get("encoder_id") or "").split("__")[0]
            rec["l1_kind"] = "surfaced-embedding" if emb_only else "ambiguous-source" if family in AMBIGUOUS_FAMILIES else "surfaced"
            if not emb_only and fw is not None and any(ct < mt < fw and cited(m, pairs, c.get("encoder_id")) for mt, m in msgs):
                rec["level"] = "L2"
        out.append(rec)
    return out


def summary(calls_by_atom: dict[str, list[dict]], n_atoms: int, relevant: set[str] | None = None) -> dict:
    """Encoder use for one score row: each atom's highest level over its answered calls on relevant families (every
    family when `relevant` is None). `share` is over atoms that called a relevant encoder; `share_all_atoms` over every
    atom, since under a natural prompt the call rate is part of the finding."""
    def rel(r):
        return relevant is None or (r.get("encoder_id") or "").split("__")[0] in relevant

    best, callers, no_outputs, fw_unknown = {}, 0, 0, 0
    for atom, recs in calls_by_atom.items():
        recs = [r for r in recs if rel(r)]
        no_outputs += sum(1 for r in recs if r["level"] is None and not r.get("declared"))
        if not recs:
            continue
        callers += 1
        graded = [r for r in recs if r["level"] is not None]
        fw_unknown += any(r["final_write_unknown"] for r in graded)
        best[atom] = max((r["level"] for r in graded), key=RANK.get) if graded else "L0"
    n = len(best)

    def share(denominator):
        return {lv: (sum(RANK[b] >= RANK[lv] for b in best.values()) / denominator if denominator else None) for lv in LEVELS}

    l1 = sum(RANK[b] >= 1 for b in best.values())
    return {"atoms_calling": callers, "atoms_n": n_atoms, "share": share(n), "share_all_atoms": share(n_atoms),
            "atoms_final_write_unknown": fw_unknown,
            "l1_to_l2_drop": (l1 - sum(b == "L2" for b in best.values())) / l1 if l1 else None,
            "answered_calls_without_outputs": no_outputs, "relevant": sorted(relevant) if relevant else "all families",
            "L3": "unmeasured (needs a paired ablation)"}
