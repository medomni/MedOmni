"""CKD by KDIGO from blood creatinine: `CKD//LABEL` (1 or 0, every patient) and `CKD//SPAN_END` (the end of the
patient's creatinine span, the CKD task's prediction time).

Why a hook: the label needs the CKD-EPI 2021 eGFR from each day's median creatinine and the patient's age that year,
then two low values at least 90 days apart. That is arithmetic across rows, which no label rule expresses (U1.10:
"CKD by KDIGO as a custom hook"). v0.2: `registry/derivations/mimic_ckd-kdigo-egfr-staging/derive_ckd_labels.py`,
unchanged in its rules: for the label, values outside (0, 50] mg/dL are dropped, age floored at 18, eGFR < 60 twice
>= 90 days apart. The span counts every creatinine row, numeric or not, as v0.2's `cr_spans.csv` does.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date


def egfr_ckdepi_2021(scr: float, age: float, female: bool) -> float:
    k = 0.7 if female else 0.9
    a = -0.241 if female else -0.302
    e = 142.0 * min(scr / k, 1.0) ** a * max(scr / k, 1.0) ** -1.200 * 0.9938 ** age
    return e * 1.012 if female else e


def _median(vs: list[float]) -> float:
    vs = sorted(vs)
    n = len(vs)
    return vs[n // 2] if n % 2 else (vs[n // 2 - 1] + vs[n // 2]) / 2


def derive(rows, raw_root, params: dict) -> list[dict]:
    creat = set(params["creatinine"])
    pats: dict[str, dict] = defaultdict(dict)
    daily: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    span_end: dict[str, str] = {}
    for r in rows:
        s, c = r["subject_id"], r["code"]
        if c.startswith("SEX//"):
            pats[s]["female"] = c == "SEX//F"
        elif c in ("AGE", "ANCHOR_YEAR"):
            pats[s][c] = r["numeric_value"]
        elif c in creat and r["time"]:
            day = str(r["time"])[:10]
            span_end[s] = max(span_end.get(s, day), day)  # the span counts every creatinine row
            if r["numeric_value"] is not None and 0 < r["numeric_value"] <= 50:  # the label counts plausible values
                daily[s][day].append(r["numeric_value"])
    out = []
    for s, p in pats.items():
        if "AGE" not in p or "ANCHOR_YEAR" not in p:
            continue
        lab_ckd = 0
        days = daily.get(s)
        if days:
            pts = []
            for d, vs in sorted(days.items()):
                y, m, dd = map(int, d.split("-"))
                age = max(18, p["AGE"] + (y - p["ANCHOR_YEAR"]))
                pts.append((date(y, m, dd), egfr_ckdepi_2021(_median(vs), age, p.get("female", False))))
            low = [d for d, e in pts if e < 60]
            lab_ckd = int(bool(low) and (low[-1] - low[0]).days >= 90)
        if s in span_end:
            out.append({"subject_id": s, "time": f"{span_end[s]}T23:59:59", "code": "CKD//SPAN_END"})
        out.append({"subject_id": s, "time": None, "code": "CKD//LABEL", "numeric_value": float(lab_ckd)})
    return out
