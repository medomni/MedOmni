"""Categorical summaries without inventing the device's posture codebook."""
import numpy as np
from contract import Degraded, labels
FAMILY = "body-position-code-10hz"


def encode(sample, options):
    x = np.asarray(sample["channels"]["position"], dtype=float)
    if not x.size or not np.isfinite(x).all():
        raise Degraded("position contains missing or non-finite codes")
    codes, counts = np.unique(x, return_counts=True)
    if len(codes) > 32:
        raise Degraded("more than 32 position codes; ambiguous categorical encoding")
    probabilities = counts / x.size
    sample["notes"].append("Device codebook unavailable; no anatomical posture mapping applied.")
    values = dict(code_count=len(codes), modal_fraction=float(probabilities.max()),
                  code_entropy=float(-np.sum(probabilities * np.log2(probabilities))),
                  transition_count=int(np.count_nonzero(x[1:] != x[:-1])))
    items = [dict(label=k, value=v, unit="bit" if k == "code_entropy" else "1") for k, v in values.items()]
    items.append(dict(label="duration", value=x.size / sample["rate_hz"], unit="s"))
    return [labels(items, "physical")]
