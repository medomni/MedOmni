"""Pulse-rate observations at native 10 Hz; no beat detection."""
import numpy as np
from medomni.perception.runtime import Degraded, labels
FAMILY = "pulse-rate-10hz-bpm"


def encode(sample, options):
    raw = np.asarray(sample["channels"]["pulse"], dtype=float)
    valid = np.isfinite(raw) & (raw > 0)
    x = raw[valid]
    excluded = int((~valid).sum())
    if excluded:
        sample["notes"].append(f"{excluded} nonpositive or non-finite pulse readings excluded.")
    if not x.size:
        raise Degraded("no valid pulse readings")
    stats = dict(min=float(x.min()), max=float(x.max()), mean=float(x.mean()),
                 median=float(np.median(x)), std=float(x.std()))
    items = [dict(label="pulse_" + k, value=v, unit="bpm") for k, v in stats.items()]
    items += [dict(label="valid_fraction", value=float(valid.mean()), unit="1"),
              dict(label="duration", value=len(raw)/sample["rate_hz"], unit="s")]
    return [labels(items, "physical")]
