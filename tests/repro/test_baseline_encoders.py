"""Check 4, encoder half: every encoder row of the baseline's `encoders.jsonl` whose encoder ships, replayed on the
rebuilt image with v0.2.1's own test input, gives the same response (the runtime block left out, as the baseline did).

BayesBeat's baseline rows were unseeded, so they are compared by shape, as `baseline.py` does; its image is seeded now.
Needs Docker, the 44 local images, v0.2.1's checkout and the baseline folder: T4. Prints counts and encoder ids only.
    pytest -m baseline tests/perception/test_baseline_encoders.py -s
"""
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

pytestmark = [pytest.mark.baseline, pytest.mark.containers]

REPO = Path(__file__).resolve().parents[2]
V02 = Path(os.environ.get("MEDOMNI_V02", "<v0.2 checkout>"))
BASELINE = Path(os.environ.get("MEDOMNI_BASELINE",
                               "<workspace>/baseline/v0.2.1/20261105-171439-run1"))
NONDETERMINISTIC = {"ppg-waveform-uncal__bayesbeat"}
WORKERS = int(os.environ.get("MEDOMNI_WORKERS", "3"))


def shape(v):
    if isinstance(v, dict):
        return {k: shape(x) for k, x in v.items()}
    if isinstance(v, list):
        return [shape(x) for x in v]
    return type(v).__name__ if isinstance(v, (int, float)) and not isinstance(v, bool) else v


def _replay(job):
    eid, name, want = job
    family = eid.split("__")[0]
    data = V02 / "perception/encoders" / eid.replace("__", "/", 1) / "testdata"
    p = subprocess.run(["docker", "run", "--rm", "--network", "none", "-v", f"{data}:/data:ro", f"ghcr.io/medomni/{eid}:dev",
                        "python", "-m", "medomni.perception.runtime.serve", "encode", "--family", family, "--path", name,
                        "--data-root", "/data"], capture_output=True, text=True)
    try:
        got = json.loads(p.stdout)
    except ValueError:
        return eid, "no response"
    got = {k: got.get(k) for k in want}
    if got == want:
        return eid, "same"
    if eid in NONDETERMINISTIC and shape(got) == shape(want):
        return eid, "same shape"
    return eid, "DIFFERS"


def test_baseline_encoder_rows_give_the_same_response():
    shipped = {f"{c.parent.parent.name}__{c.parent.name}" for c in (REPO / "perception/encoders").glob("*/*/card.yaml")}
    rows = [json.loads(line) for line in (BASELINE / "encoders.jsonl").read_text().splitlines()]
    jobs = [(r["encoder"], r["input"], r["response"]) for r in rows if r["encoder"] in shipped]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(_replay, jobs))
    bad = sorted({eid for eid, outcome in res if outcome not in ("same", "same shape")})
    print(f"\nbaseline encoder rows: {len(rows)}; shipped {len(jobs)}; "
          f"same {sum(o == 'same' for _, o in res)}; same shape {sum(o == 'same shape' for _, o in res)}; differ {bad}")
    assert len(jobs) == 105 and not bad  # 117 rows, 12 of them for unshipped encoders (R-63)
