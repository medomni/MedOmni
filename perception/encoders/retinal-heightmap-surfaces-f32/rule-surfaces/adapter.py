"""Surface statistics in stored coordinates, without invented anatomical mapping."""
import numpy as np
from contract import Degraded, labels
FAMILY = "retinal-heightmap-surfaces-f32"


def encode(sample, options):
    pixels = sample["pixels"]
    if not pixels.size or not np.isfinite(pixels).all():
        raise Degraded("heightmap contains empty or non-finite surfaces")
    items = [dict(label="surface_count", value=int(pixels.shape[0]), unit="1")]
    for index, plane in enumerate(pixels):
        x = plane.astype(np.float64)
        items += [dict(label=f"surface_{index}_mean", value=float(x.mean()), unit=None),
                  dict(label=f"surface_{index}_range", value=float(np.ptp(x)), unit=None)]
    sample["notes"].append("Stored depth coordinates only; no anatomical surface names or calibrated thickness.")
    return [labels(items, "physical")]
