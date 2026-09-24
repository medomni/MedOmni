"""Foveal avascular zone and parafoveal vessel density from a superficial OCTA en-face slab.

Rules, not a model. The foveal avascular zone (FAZ) is the dark connected region around the darkest
point near the scan centre, on the slab smoothed at 30 um, cut midway between the FAZ interior and
the surrounding capillary bed. Vessels are separated from background by Otsu's threshold on the
lightly smoothed slab; vessel density is the vessel share of the ETDRS parafovea (1-3 mm annulus)
centred on the FAZ. Where a published norm exists for the device, slab and
metric, a z-score is reported.
"""
import numpy as np
from scipy import ndimage
from contract import Degraded, labels, text
from norms import NORMS

FAMILY = "octa-enface-slab-mono8-2d"
FOVEA_SEARCH_MM = 1.5
VESSEL_SMOOTH_MM = 0.01
FAZ_SMOOTH_MM = 0.03
FAZ_CORE_MM = 0.05                  # radius around the seed that samples the FAZ interior
FAZ_BED_MM = (0.5, 1.0)             # annulus around the seed that samples the capillary bed
FAZ_MAX_MM2 = 1.5                   # a larger avascular region is not a FAZ (non-perfusion or poor signal)
PARAFOVEA = (0.5, 1.5)              # radius in mm


def _otsu(values):
    hist, edges = np.histogram(values, bins=256, range=(0, 256))
    p = hist / hist.sum()
    omega, mu = np.cumsum(p), np.cumsum(p * np.arange(256))
    with np.errstate(invalid="ignore", divide="ignore"):
        between = (mu[-1] * omega - mu) ** 2 / (omega * (1 - omega))
    return float(np.nanargmax(between))


def _device(acquisition):
    model = (acquisition.get("model") or "").lower()
    return next((key for key in ("spectralis", "maestro2", "triton", "cirrus") if key in model), None)


def encode(sample, options):
    image = sample["pixels"]
    notes = sample["notes"]
    acquisition = sample.get("acquisition") or {}
    spacing = acquisition.get("pixel_spacing_mm")
    if image.ndim != 2 or not spacing or min(spacing) <= 0:
        raise Degraded("needs one en-face slab with lateral pixel spacing")
    protocol = (acquisition.get("protocol") or "").lower()
    structure = (acquisition.get("anatomic_structure") or "").lower()
    if any(key in protocol for key in ("onh", "disc", "optic")) or "optic" in structure:
        # A valid slab of this family, but not a macula: say so rather than measure the wrong anatomy.
        return [labels([], "physical"), labels([], "score"),
                text(f"Optic-disc slab (protocol '{acquisition.get('protocol')}'): macular FAZ and parafoveal density do not apply; no measurement.")]
    if not ("fovea" in structure or "mac" in protocol):
        raise Degraded("slab is not identified as macular (no fovea structure or macular protocol)")
    comments = (acquisition.get("image_comments") or "").lower()
    slab = "superficial" if comments.startswith("superficial") else None
    if slab is None:
        notes.append("Slab not identified as superficial; values are reported without a reference.")

    pixel = float(np.mean(spacing))
    smooth = ndimage.gaussian_filter(image.astype(np.float64), VESSEL_SMOOTH_MM / pixel)
    threshold = _otsu(smooth)
    vessels = smooth > threshold
    rows, cols = image.shape
    y = (np.arange(rows) - (rows - 1) / 2) * spacing[0]
    x = (np.arange(cols) - (cols - 1) / 2) * spacing[1]
    yy, xx = np.meshgrid(y, x, indexing="ij")

    # FAZ seed: darkest point of a heavily smoothed slab within the search radius of the scan centre.
    coarse = ndimage.gaussian_filter(image.astype(np.float64), 0.1 / pixel)
    coarse[np.hypot(yy, xx) > FOVEA_SEARCH_MM] = np.inf
    sy, sx = np.unravel_index(np.argmin(coarse), coarse.shape)
    faz_smooth = ndimage.gaussian_filter(image.astype(np.float64), FAZ_SMOOTH_MM / pixel)
    around = np.hypot(yy - y[sy], xx - x[sx])
    core = float(np.median(faz_smooth[around <= FAZ_CORE_MM]))
    bed = float(np.median(faz_smooth[(around >= FAZ_BED_MM[0]) & (around < FAZ_BED_MM[1])]))
    if bed - core < 10:
        raise Degraded(f"no contrast between the fovea ({core:.0f}) and the capillary bed ({bed:.0f})")
    regions, _ = ndimage.label(faz_smooth < (core + bed) / 2)
    faz = ndimage.binary_fill_holes(regions == regions[sy, sx])
    faz_area = float(faz.sum() * spacing[0] * spacing[1])
    if faz_area > FAZ_MAX_MM2 or faz[0].any() or faz[-1].any() or faz[:, 0].any() or faz[:, -1].any():
        raise Degraded(f"avascular region at the fovea is {faz_area:.2f} mm2 or reaches the scan edge; "
                       "not measurable as a FAZ (poor signal or non-perfusion)")
    cy, cx = (float(v) for v in ndimage.center_of_mass(faz))
    radius = np.hypot(yy - np.interp(cy, np.arange(rows), y), xx - np.interp(cx, np.arange(cols), x))
    ring = (radius >= PARAFOVEA[0]) & (radius < PARAFOVEA[1])
    coverage = ring.sum() * spacing[0] * spacing[1] / (np.pi * (PARAFOVEA[1] ** 2 - PARAFOVEA[0] ** 2))
    values = [dict(label="faz_area_mm2", value=round(faz_area, 3), unit="mm2")]
    density = None
    if coverage >= 0.8:
        density = float(vessels[ring].mean())
        values.append(dict(label="parafovea_vessel_density", value=round(density, 3), unit="1"))
    else:
        notes.append("Parafovea not covered by the scan; density omitted.")
    values.append(dict(label="fovea_offset_mm", value=round(float(np.hypot(np.interp(cy, np.arange(rows), y),
                                                                            np.interp(cx, np.arange(cols), x))), 3), unit="mm"))

    device = _device(acquisition)
    reference = NORMS.get((device, slab)) if slab else None
    scores, sentences = [], []
    for label, value, unit in (("faz_area_mm2", faz_area, "mm2"), ("parafovea_vessel_density", density, "")):
        if value is None:
            continue
        norm = (reference or {}).get(label)
        shown = f"{value:.2f} {unit}".strip() if unit else f"{value:.2f}"
        if norm:
            z = (value - norm[0]) / norm[1]
            flag = "below" if z < -2 else "above" if z > 2 else "within"
            scores.append(dict(label=label.replace("_mm2", "") + "_z", value=round(z, 2)))
            sentences.append(f"{'FAZ area' if label.startswith('faz') else 'parafoveal vessel density'} "
                             f"{shown} ({flag} norm {norm[0]:.2f}+-{norm[1]:.2f}, z {z:+.1f})")
        else:
            sentences.append(f"{'FAZ area' if label.startswith('faz') else 'parafoveal vessel density'} {shown} (no reference)")
    summary = f"OCTA {slab or 'unidentified'} slab ({acquisition.get('model')}): " + "; ".join(sentences) + "."
    if reference and scores:
        summary += f" Reference: {reference['source']} (unreviewed)."
    notes.append(f"Otsu threshold {threshold:.0f} on the slab smoothed at {VESSEL_SMOOTH_MM * 1000:.0f} um; "
                 f"pixel {spacing[0]:.4f} x {spacing[1]:.4f} mm.")
    return [labels(values, "physical"), labels(scores, "score"), text(summary)]
