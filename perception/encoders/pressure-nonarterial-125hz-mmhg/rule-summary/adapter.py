"""Descriptive CVP, PAP and ICP summaries; no learned or diagnostic claims."""
import numpy as np
from medomni.perception.runtime import Degraded, labels

FAMILY = "pressure-nonarterial-125hz-mmhg"
# No CVP, PAP or ICP is physically measured outside this span; values there come from an
# unzeroed transducer, a flush or a mislabeled channel. Reported, never removed.
POSSIBLE_MMHG = (-20.0, 150.0)


def encode(sample, options):
    items = []
    rate = sample["rate_hz"]
    for role in sample.get("order") or sorted(sample["channels"]):
        x = np.asarray(sample["channels"][role], dtype=float)
        valid = x[np.isfinite(x)]
        if not valid.size:
            raise Degraded(f"{role}: no valid samples")
        p05, median, p95 = np.percentile(valid, [5, 50, 95])
        stats = dict(median=median, mean=valid.mean(), p05=p05, p95=p95, std=valid.std())
        items.extend(dict(label=f"{role}_{key}", value=float(value), unit="mmHg")
                     for key, value in stats.items())
        outside = float(np.mean((valid < POSSIBLE_MMHG[0]) | (valid > POSSIBLE_MMHG[1])))
        items.append(dict(label=f"{role}_implausible_fraction", value=outside, unit="fraction"))
        items.append(dict(label=f"{role}_valid_fraction", value=valid.size / x.size, unit="fraction"))
        items.append(dict(label=f"{role}_duration", value=x.size / rate, unit="s"))
        if outside > 0.5:
            sample["notes"].append(
                f"{role}: {100 * outside:.0f}% of samples outside {POSSIBLE_MMHG[0]:g} to "
                f"{POSSIBLE_MMHG[1]:g} mmHg; likely an unzeroed transducer, flush or mislabeled channel")
    if not items:
        raise Degraded("no protocol channels")
    return [labels(items, "physical")]
