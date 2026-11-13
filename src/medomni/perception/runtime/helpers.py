"""Functions several adapters share, kept once here (R-117). Each was byte-for-byte the same in every adapter that used
it, so moving it changes no output. Heavy libraries are imported inside each function, so importing this module
needs none of them.
"""
from .errors import Degraded
from .response import labels


def amplitude_features(sample, options):
    """Descriptive amplitude features per channel: mean, std, RMS, peak-to-peak, duration (the rule-amplitude
    encoders of 5 families)."""
    import numpy as np

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


def intensity_features(sample, options):
    """Uncalibrated intensity features of a stored image (the rule-intensity encoders of 5 families)."""
    import numpy as np

    pixels = sample["pixels"]
    if not pixels.size or not np.isfinite(pixels).all():
        raise Degraded("empty or non-finite pixels")
    histogram = np.bincount(pixels.reshape(-1), minlength=256)
    probabilities = histogram[histogram > 0] / pixels.size
    items = [
        dict(label="intensity_mean", value=float(np.mean(pixels, dtype=np.float64)), unit="stored-value"),
        dict(label="intensity_std", value=float(np.std(pixels, dtype=np.float64)), unit="stored-value"),
        dict(label="zero_fraction", value=float(histogram[0]/pixels.size), unit="1"),
        dict(label="saturated_fraction", value=float(histogram[255]/pixels.size), unit="1"),
        dict(label="intensity_entropy", value=float(-np.sum(probabilities*np.log2(probabilities))), unit="bit"),
        dict(label="frame_count", value=int(pixels.shape[0]) if pixels.ndim == 3 else 1, unit="1"),
    ]
    return [labels(items, "physical")]


def check_norm_unused(state):
    """The checkpoint carries BatchNorm tensors, and the network runs without them.

    That pairing looks like a mistake — weights loaded and then ignored — so it
    is checked instead of trusted. In the published checkpoint every BatchNorm
    tensor is still at its initialization value: scale one, shift zero, running
    mean zero, running variance one, no batches tracked. That is what a network
    trained with use_bn=False leaves behind, and it is why running it with
    use_bn=False discards nothing.

    A future checkpoint with trained statistics would be silently wrong here, so
    it must fail at start rather than answer.
    """
    import torch

    at_init = {"weight": 1.0, "bias": 0.0, "running_mean": 0.0, "running_var": 1.0,
               "num_batches_tracked": 0}
    for key, tensor in state.items():
        field = key.rsplit(".", 1)[-1]
        if "bn" not in key or field not in at_init:
            continue
        if not torch.all(tensor.to(torch.float64) == at_init[field]):
            raise RuntimeError(
                f"{key} holds trained statistics, but this network runs with "
                "use_bn=False and would ignore them. Refusing to answer with a "
                "model that is not the one the weights describe.")
