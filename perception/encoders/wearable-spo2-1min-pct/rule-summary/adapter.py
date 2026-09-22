"""Observed SpO2 summaries; no interpolation or clinical classification."""
import numpy as np
from contract import Degraded, labels

FAMILY = "wearable-spo2-1min-pct"


def encode(sample, options):
    values = np.asarray(sample["values"], dtype=float)
    valid = np.isfinite(values) & (values > 0) & (values <= 100)
    excluded = int((~valid).sum())
    if excluded:
        sample["notes"].append(f"{excluded} non-finite or outside (0, 100] readings excluded.")
    x = values[valid]
    if not x.size:
        raise Degraded("no usable positive SpO2 readings")
    stats = dict(min=float(x.min()), max=float(x.max()), mean=float(x.mean()),
                 median=float(np.median(x)), std=float(x.std()))
    items = [dict(label="spo2_" + k, value=v, unit="%") for k, v in stats.items()]
    items.extend([
        dict(label="valid_count", value=int(x.size), unit="1"),
        dict(label="excluded_count", value=excluded, unit="1"),
        dict(label="observed_span", value=(sample["times"][-1] - sample["times"][0]).total_seconds(), unit="s"),
    ])
    return [labels(items, "physical")]
