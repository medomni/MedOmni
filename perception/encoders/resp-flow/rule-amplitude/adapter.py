"""Descriptive signal amplitude features; no learned or diagnostic claims."""
import numpy as np
from contract import Degraded, labels

FAMILY = "resp-flow"


def encode(sample, options):
    items = []
    for name, raw in sample["channels"].items():
        x = np.asarray(raw, dtype=float)
        if not x.size or not np.isfinite(x).all():
            raise Degraded(f"{name}: empty or non-finite signal")
        rate = sample.get("rates", {}).get(name, sample.get("rate_hz"))
        unit = sample.get("channel_units", {}).get(name, sample.get("units"))
        # Scaling avoids overflow in squaring physically valid large amplitudes.
        amplitude = float(np.max(np.abs(x)))
        rms = float(amplitude * np.sqrt(np.mean((x / amplitude) ** 2))) if amplitude else 0.0
        stats = dict(mean=float(x.mean()), std=float(x.std()), rms=rms,
                     peak_to_peak=float(np.ptp(x)))
        if not all(np.isfinite(v) for v in stats.values()):
            raise Degraded(f"{name}: signal magnitude exceeds numeric range")
        items.extend(dict(label=name.replace("-", "_") + "_" + key, value=value, unit=unit)
                     for key, value in stats.items())
        items.append(dict(label=name.replace("-", "_") + "_duration", value=len(x) / rate, unit="s"))
    if not items:
        raise Degraded("no protocol channels")
    return [labels(items, "physical")]
