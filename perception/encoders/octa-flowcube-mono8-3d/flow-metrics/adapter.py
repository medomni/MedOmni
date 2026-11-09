"""flow-metrics — quantitative flow signal from an OCTA cube.

A rule extractor, not a model. OCTA's own literature quantifies angiograms with
a handful of measures computed from the image, and those measures are what a
reader can actually use: how much of the projected field carries flow signal,
how long the perfused network is, and where in depth the flow sits. Nothing
here is learned, so nothing here has a training distribution to fall outside of.

Two choices are the adapter's, and the card states both:

  * **The en-face projection is the mean along depth**, not the maximum. A
    maximum projection is the convention for a segmented slab; over a whole
    cube it reports the brightest voxel in a column, which in a cube that
    includes the choroid is usually not the retinal vasculature.
  * **Binarisation uses Otsu's threshold**, computed per image by
    scikit-image. Vessel area density has no meaning without a threshold, and a
    fixed one would be a clinical constant we have no standing to choose. Otsu
    is derived from the image itself, and the threshold it chose is reported
    beside the density it produced.

Card: card.yaml   Contract: perception/spec/container-api.md §5
"""
import numpy as np

from medomni.perception.runtime import Degraded, labels

FAMILY = "octa-flowcube-mono8-3d"

PRECISION = 4


def _threshold_and_skeleton(enface):
    """Otsu's threshold and the skeleton of what it selects.

    Both come from scikit-image rather than from code here. The measures are
    the literature's, and using the implementation the literature uses is what
    makes a number comparable with a published one; a hand-rolled thinning
    agreed with this one to within four percent, which is four percent of
    disagreement nobody would be able to account for later.
    """
    from skimage.filters import threshold_otsu
    from skimage.morphology import skeletonize
    if int(enface.max()) == int(enface.min()):
        raise Degraded("the projection is one value everywhere; there is nothing to threshold")
    threshold = int(threshold_otsu(enface))
    vessels = enface > threshold
    return threshold, vessels, int(skeletonize(vessels).sum())


def encode(sample, options):
    cube = sample["pixels"]
    if cube.ndim != 3:
        raise Degraded(f"this family is a stack of B-scans; the decoder returned "
                       f"{cube.ndim} dimension(s)")
    n_frames = int(cube.shape[0])
    # Which frames carry nothing is a property of the data rather than of this
    # model, but the family decoder reports pixels alone, so it is measured here
    # and reported rather than silently averaged in.
    blank = {i for i in range(n_frames) if int(cube[i].max()) == int(cube[i].min())}
    usable = [i for i in range(n_frames) if i not in blank]
    if not usable:
        raise Degraded("every B-scan is blank")
    if len(usable) < n_frames:
        sample["notes"].append(
            f"{n_frames - len(usable)} blank B-scan(s) excluded from every measure")

    flow = cube[usable].astype(np.float64)
    # En-face: average along depth, one value per (B-scan, A-scan position).
    enface = flow.mean(axis=1)
    quantised = np.clip(np.rint(enface), 0, 255).astype(np.uint8)
    threshold, vessels, length = _threshold_and_skeleton(quantised)
    area_density = float(vessels.mean())

    # Depth profile: the mean flow signal of each axial row, summarised by where
    # its centre of mass lies. A cube with flow concentrated superficially and
    # one with flow throughout differ here and nowhere else in this readout.
    depth_profile = flow.mean(axis=(0, 2))
    weights = depth_profile.sum()
    if weights <= 0:
        raise Degraded("the cube carries no flow signal at any depth")
    depth_index = np.arange(depth_profile.size, dtype=np.float64)
    centroid = float((depth_profile * depth_index).sum() / weights) / depth_profile.size

    items = [
        {"label": "flow_mean", "value": round(float(flow.mean()), PRECISION)},
        {"label": "flow_sd", "value": round(float(flow.std(ddof=1)), PRECISION)},
        {"label": "flow_p50", "value": round(float(np.percentile(flow, 50)), PRECISION)},
        {"label": "flow_p95", "value": round(float(np.percentile(flow, 95)), PRECISION)},
        {"label": "enface_otsu_threshold", "value": float(threshold)},
        {"label": "vessel_area_density", "value": round(area_density, PRECISION)},
        {"label": "vessel_length_density",
         "value": round(length / float(vessels.size), PRECISION)},
        {"label": "flow_depth_centroid", "value": round(centroid, PRECISION)},
        {"label": "n_bscans", "value": float(len(usable))},
    ]
    sample["notes"].append(
        f"measures computed over {len(usable)} B-scan(s); en-face is the mean along depth, "
        f"binarised at Otsu threshold {threshold}")
    return [labels(items, scale="physical")]
