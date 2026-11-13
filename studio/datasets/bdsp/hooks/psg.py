"""BDSP sleep studies: each patient's latest night on disk, its sleep metrics and the EHR demographics.

Why a hook (in v0.2 these rules were spread over its BDSP adapter, PSG derivation and manifest catalog):

- **The night.** A patient's study is the latest session whose h5 night is on disk. "Latest that exists" is a choice
  across rows and files, which no reader option makes. Its rows: `RECORDING//START`, `RECORDING//END` (start plus
  the recorded duration), `DEMO//SEX//<sex>`, `DEMO//AGE`, and one `FILE//<family>` per family the night carries,
  by the converter's own channel rule (`h5_to_edf.available`, channel names only).
- **Sleep metrics** from the technologist's scoring (`*_scores.csv` stages, `*_events.csv` events), each raw label
  classified by `vocab.yaml`: efficiency, REM and N3 fractions, and the AHI, arousal and limb indices per hour of
  sleep. An unclassified raw label stops the load: it is never silently dropped (`check` lists them for
  `bench data check`).
- **Demographics** from the EHR: race through `vocab.yaml`, and the date of death as the end of that day.

The rules are v0.2's, unchanged; nights without scored sleep have no metrics.
"""
from __future__ import annotations

import csv
import glob as globmod
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
BUCKETS = ("w", "n1", "n2", "n3", "r")


@lru_cache(maxsize=None)
def vocab() -> dict:
    return yaml.safe_load((HERE.parent / "vocab.yaml").read_text(encoding="utf-8"))


def classify(section: str, label: str) -> str | None:
    sec = vocab().get(section, {})
    if label in (sec.get("labels") or {}):
        return sec["labels"][label]
    for pat in sec.get("patterns") or []:
        if re.fullmatch(pat["regex"], label):
            return pat["class"]
    return None


def _rows(raw_root: Path, pattern: str) -> list[dict]:
    from medomni.core.loading.readers.csv_ import read_table

    out = []
    for p in sorted(globmod.glob(str(raw_root / pattern))):
        out += read_table(Path(p))
    return out


def h5_path(params: dict, m: dict) -> str:
    return params["night"].format(folder=m["BIDSFolder"], session=m["SessionID"])


def nights(raw_root: Path, params: dict) -> dict[str, dict]:
    """patient id -> the session row of the latest night on disk (v0.2's `bdsp_sessions`)."""
    out: dict[str, dict] = {}
    for m in _rows(raw_root, params["metadata"]):
        pid = m["BDSPPatientID"]
        if (raw_root / h5_path(params, m)).exists() and (pid not in out or m["StartDateTime"] > out[pid]["StartDateTime"]):
            out[pid] = m
    return out


def _counts(path: Path, column: str) -> Counter | None:
    if not path.exists():
        return Counter()
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            return Counter((r.get(column) or "").strip() for r in csv.DictReader(f))
    except (OSError, csv.Error):
        return None  # an unreadable events file: its metrics are left out, never zero


@lru_cache(maxsize=None)
def scoring(raw_root: Path, rel_h5: str) -> tuple[Counter, Counter | None]:
    """A night's stage and event label counts (cached: `check` and the load both need them, and exFAT is slow)."""
    h5 = raw_root / rel_h5
    return (_counts(h5.with_name(h5.name.replace(".h5", "_scores.csv")), "Sleep_Stage") or Counter(),
            _counts(h5.with_name(h5.name.replace(".h5", "_events.csv")), "Event"))


def metrics(stages: Counter, events: Counter | None) -> dict[str, float]:
    st, ev = Counter(), Counter()
    for lab, n in stages.items():
        st[classify("psg_stages", lab)] += n
    for lab, n in (events or {}).items():
        ev[classify("psg_events", lab)] += n
    scored = sum(st[k] for k in BUCKETS)
    sleep = scored - st["w"]
    tst_h = sleep * 30 / 3600
    out = {"EFFICIENCY": round(sleep / scored, 4) if scored else None,
           "REM_FRACTION": round(st["r"] / sleep, 4) if sleep else None,
           "N3_FRACTION": round(st["n3"] / sleep, 4) if sleep else None}
    if events is not None and tst_h > 0:
        out |= {"AHI": round(ev["resp"] / tst_h, 2), "AROUSAL_INDEX": round(ev["arousal"] / tst_h, 2),
                "LIMB_INDEX": round(ev["limb"] / tst_h, 2)}
    return {k: v for k, v in out.items() if v is not None}


def unclassified(raw_root: Path, params: dict, found: dict | None = None) -> list[str]:
    """Raw labels the vocabulary does not classify, as `<section>:<label>`, for the patients with a night on disk
    (the label vocabulary check)."""
    found = nights(raw_root, params) if found is None else found
    bad = set()
    for m in found.values():
        stages, events = scoring(raw_root, h5_path(params, m))
        bad |= {f"psg_stages:{lab}" for lab in stages if classify("psg_stages", lab) is None}
        bad |= {f"psg_events:{lab}" for lab in events or {} if classify("psg_events", lab) is None}
    for r in _rows(raw_root, params["demographics"]):
        lab = (r.get("race") or "").strip()
        if r["bdsp_patient_id"] in found and classify("bdsp_race", lab) is None:
            bad.add(f"bdsp_race:{lab}")
    return sorted(bad)


def converter():
    """This package's h5-to-edf converter module, loaded by path (R-145)."""
    from medomni.core.loading.hooks import file_module

    return file_module(HERE.parent, "converters/h5_to_edf.py", "converter")


def _start(m: dict) -> str:
    return m["StartDateTime"][:19]


def derive(rows, raw_root: Path, params: dict) -> list[dict]:
    from datetime import datetime, timedelta

    h5_to_edf = converter()
    found = nights(raw_root, params)
    bad = unclassified(raw_root, params, found)
    if bad:
        from medomni.core.loading import LoadError

        raise LoadError(f"read: hook psg: {len(bad)} raw label(s) vocab.yaml does not classify: {', '.join(bad)}")
    out = []
    families = tuple(params["families"])
    for pid, m in found.items():
        start = _start(m)
        rel = h5_path(params, m)
        dur = int(float(m.get("RecordingDuration") or 0))
        end = (datetime.fromisoformat(start.replace(" ", "T")) + timedelta(seconds=dur)).isoformat(sep=" ")
        out += [{"subject_id": pid, "time": start, "code": "RECORDING//START"},
                {"subject_id": pid, "time": end, "code": "RECORDING//END"}]
        if m.get("SexDSC"):
            out.append({"subject_id": pid, "time": None, "code": f"DEMO//SEX//{m['SexDSC'].strip().lower()}"})
        if m.get("AgeAtVisit") not in ("", None):
            out.append({"subject_id": pid, "time": None, "code": "DEMO//AGE", "numeric_value": float(m["AgeAtVisit"])})
        import h5py

        with h5py.File(raw_root / rel, "r") as f:
            names = list(f["signals"].keys())
            out += [{"subject_id": pid, "time": start, "code": f"FILE//{fam}", "path": rel}
                    for fam in families if h5_to_edf.available(names, fam)
                    and (fam not in params.get("rate_enforced", ()) or h5_to_edf.rate_accepted(f["signals"], fam))]
        stages, events = scoring(raw_root, rel)
        out += [{"subject_id": pid, "time": end, "code": f"SLEEP//{k}", "numeric_value": v}
                for k, v in metrics(stages, events).items()]
    for r in _rows(raw_root, params["demographics"]):
        pid = r["bdsp_patient_id"]
        if pid not in found:
            continue
        race = classify("bdsp_race", (r.get("race") or "").strip())
        if race:
            out.append({"subject_id": pid, "time": None, "code": f"DEMO//RACE//{race}"})
        if r.get("shifted_date_of_death"):
            out.append({"subject_id": pid, "time": f"{r['shifted_date_of_death'][:10]}T23:59:59", "code": "DEATH"})
    return out


def inputs(raw_root: Path, params: dict) -> list[str]:
    """The metadata and demographics tables; each night's h5 and scoring files."""
    out = [Path(p).relative_to(raw_root).as_posix()
           for pat in (params["metadata"], params["demographics"]) for p in sorted(globmod.glob(str(raw_root / pat)))]
    for m in nights(raw_root, params).values():
        rel = h5_path(params, m)
        out += [rel] + [rel.replace(".h5", s) for s in ("_scores.csv", "_events.csv")
                        if (raw_root / rel.replace(".h5", s)).exists()]
    return out


def dummy(raw_root: Path, subjects: dict, params: dict, rng) -> None:
    """A metadata table, one scored night per subject (all families), and the EHR demographics."""
    from datetime import timedelta

    from medomni.core.families import get
    from medomni.core.families.dummy.signal import write_h5

    meta = Path(raw_root) / params["metadata"].replace("*", "dummy")
    meta.parent.mkdir(parents=True, exist_ok=True)
    cols = ["SiteID", "BDSPPatientID", "BIDSFolder", "SessionID", "StartDateTime", "RecordingDuration", "AgeAtVisit",
            "SexDSC"]
    with open(meta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for i, (s, t0) in enumerate(sorted(subjects.items())):
            w.writerow(["I0006", s, f"sub-{s}", 1, (t0 + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), 3600,
                        40 + i, "Female" if i % 2 else "Male"])
    for i, (s, t0) in enumerate(sorted(subjects.items())):
        m = {"BIDSFolder": f"sub-{s}", "SessionID": 1}
        h5 = Path(raw_root) / h5_path(params, m)
        h5.parent.mkdir(parents=True, exist_ok=True)
        write_h5([get(f) for f in params["families"]], i, h5, subject=s, start=t0 + timedelta(hours=2))
        stages = ["W", "N1", "N2", "N3", "R"] * 24
        with open(h5.with_name(h5.name.replace(".h5", "_scores.csv")), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["Sleep_Stage"])
            w.writerows([st] for st in stages)
        with open(h5.with_name(h5.name.replace(".h5", "_events.csv")), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["Event"])
            w.writerows([e] for e in ["Hypopnea"] * (i * 3) + ["LM"] * i)
    demo = Path(raw_root) / params["demographics"].replace("*", "dummy")
    demo.parent.mkdir(parents=True, exist_ok=True)
    import pyarrow as pa
    import pyarrow.parquet as pq

    ids = sorted(subjects)
    pq.write_table(pa.table({"bdsp_patient_id": ids, "race": ["Asian" if i % 3 else "" for i in range(len(ids))],
                             "shifted_date_of_death": ["" for _ in ids]}), demo)


def problems(raw_root: Path, params: dict) -> list[str]:
    """`bench data check`: every raw label the label vocabulary does not classify (v0.2's labelvocab gate)."""
    return [f"raw label not classified in vocab.yaml: {x}" for x in unclassified(raw_root, params)]


def demographics(subjects, raw_root: Path, params: dict) -> dict[str, dict]:
    """What Build shows of a patient's study, from the latest night's metadata row (evidence rules name this hook as
    `views`)."""
    found, out = nights(raw_root, params), {}
    for s in subjects:
        m = found[s]
        out[s] = {"sex": m["SexDSC"], "age_at_visit": m["AgeAtVisit"],
                  "study_type": m.get("StudyType") or m.get("StudyTypeName"), "session_start": m["StartDateTime"][:19]}
    return out
