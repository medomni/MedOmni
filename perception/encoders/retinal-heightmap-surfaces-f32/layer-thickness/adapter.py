"""Retinal layer thickness per ETDRS region from device-exported surfaces, against published norms.

Rules, not a model. Each frame of the heightmap is one segmented surface, its depth in the
device's A-scan pixels. The adapter names the surfaces, converts depth to micrometres with the
device's axial pixel size, locates the fovea as the thinnest point near the scan centre, and
reports thickness in the ETDRS centre (1 mm), inner ring (1-3 mm) and outer ring (3-6 mm).
Where a published normative mean and SD exist for the device, each thickness gets a z-score and
a below/within/above flag at +-2 SD.
"""
import numpy as np
from contract import Degraded, labels, text
from norms import AXIAL_UM, NORMS

FAMILY = "retinal-heightmap-surfaces-f32"

# Anatomical depth rank of every surface label the supply uses (inner to outer). A label is the
# posterior boundary of the layer it names (Spectralis 'RNFL' = RNFL/GCL boundary).
RANK = {"ILM": 0, "RNFL": 1, "RNFL/GCL": 1, "GCL": 2, "GCL/IPL": 2, "IPL": 3, "IPL/INL": 3,
        "INL": 4, "INL/OPL": 4, "OPL": 5, "OPL/ONL": 5, "ELM": 6, "PR1": 7, "IS/OS": 7, "EZ": 7,
        "PR2": 8, "IZ": 8, "RPE": 9, "OS/RPE": 9, "BM": 10, "CSI": 11}
MISSING = 1e30                       # Spectralis marks unsegmented points with FLT_MAX
FOVEA_SEARCH_MM = 1.0                # the thinnest point within this radius of the scan centre
SMOOTH_MM = 0.2
REGIONS = (("center", 0.0, 0.5), ("inner", 0.5, 1.5), ("outer", 1.5, 3.0))
MIN_COVERAGE = 0.8                   # share of a region's area that must lie inside the scan


def _device(acquisition):
    model = (acquisition.get("model") or "").lower()
    for key in AXIAL_UM:
        if key in model:
            return key
    return None


def _name_surfaces(pixels, surfaces, notes):
    """Map canonical names to frame indices; frames whose file labels contradict depth are reordered by depth."""
    if any(label not in RANK for label in surfaces):
        unknown = sorted({str(label) for label in surfaces if label not in RANK})
        raise Degraded(f"surface labels not recognised: {', '.join(unknown)}")
    depth = [float(np.nanmedian(plane)) for plane in pixels]
    by_label = sorted(range(len(surfaces)), key=lambda i: (RANK[surfaces[i]], i))
    by_depth = sorted(range(len(surfaces)), key=lambda i: (depth[i], i))
    if [RANK[surfaces[i]] for i in by_label] != [RANK[surfaces[i]] for i in by_depth]:
        # The frames are depth-ordered but their labels are not (Topcon exports): surfaces cannot
        # cross, so the k-th shallowest frame is the k-th label in anatomical order.
        labels_in_order = [surfaces[i] for i in by_label]
        notes.append("File surface labels contradict their depth order; surfaces named by anatomical depth order.")
        return {label: frame for label, frame in zip(labels_in_order, by_depth)}
    return {surfaces[i]: i for i in range(len(surfaces))}


def _region(acquisition):
    """'macula', 'disc' or None, from the acquisition protocol name."""
    protocol = (acquisition.get("protocol") or "").lower()
    if any(key in protocol for key in ("onh", "disc", "optic")):
        return "disc"
    if "mac" in protocol:
        return "macula"
    return None


def _first(named, *labels_):
    for label in labels_:
        if label in named:
            return label
    return None


def _smooth(plane, size):
    if size < 2:
        return plane
    kernel = np.ones(size) / size
    valid = np.isfinite(plane)
    filled = np.where(valid, plane, 0.0)
    num = np.apply_along_axis(lambda r: np.convolve(r, kernel, "same"), 1, filled)
    num = np.apply_along_axis(lambda c: np.convolve(c, kernel, "same"), 0, num)
    den = np.apply_along_axis(lambda r: np.convolve(r, kernel, "same"), 1, valid.astype(float))
    den = np.apply_along_axis(lambda c: np.convolve(c, kernel, "same"), 0, den)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0.5, num / den, np.nan)


def encode(sample, options):
    pixels = sample["pixels"].astype(np.float64)
    notes = sample["notes"]
    pixels[~np.isfinite(pixels) | (np.abs(pixels) >= MISSING)] = np.nan
    acquisition = sample.get("acquisition") or {}
    surfaces = sample.get("surfaces") or []
    if len(surfaces) != pixels.shape[0] or any(label is None for label in surfaces):
        raise Degraded("the file does not name its surfaces")
    spacing = acquisition.get("pixel_spacing_mm")
    if not spacing or min(spacing) <= 0:
        raise Degraded("the file carries no lateral pixel spacing")
    region = _region(acquisition)
    if region == "disc":
        # A valid heightmap of this family, but not a macula: say so rather than measure the wrong anatomy.
        return [labels([], "physical"), labels([], "score"),
                text(f"Optic-disc scan (protocol '{acquisition.get('protocol')}'): macular ETDRS thickness does not apply; no measurement.")]
    if region != "macula":
        raise Degraded(f"protocol '{acquisition.get('protocol')}' is not identified as macular or optic-disc")
    device = _device(acquisition)
    if device is None:
        raise Degraded(f"no axial pixel size known for device model '{acquisition.get('model')}'")
    axial = AXIAL_UM[device]
    named = _name_surfaces(pixels, surfaces, notes)
    outer = _first(named, "BM", "RPE", "OS/RPE")
    if "ILM" not in named or outer is None:
        raise Degraded("total retinal thickness needs the ILM and an outer boundary (BM or RPE)")
    total = (pixels[named[outer]] - pixels[named["ILM"]]) * axial
    total[total < 0] = np.nan
    if np.isnan(total).mean() > 0.5:
        raise Degraded("more than half of the thickness map is unsegmented")

    rows, cols = total.shape
    y = (np.arange(rows) - (rows - 1) / 2) * spacing[0]
    x = (np.arange(cols) - (cols - 1) / 2) * spacing[1]
    yy, xx = np.meshgrid(y, x, indexing="ij")
    smooth = _smooth(total, 2 * int(round(SMOOTH_MM / 2 / min(spacing))) + 1)   # odd width keeps the grid centred
    search = np.where(np.hypot(yy, xx) <= FOVEA_SEARCH_MM, smooth, np.nan)
    if np.isnan(search).all():
        raise Degraded("no segmented point near the scan centre")
    fy, fx = np.unravel_index(np.nanargmin(search), search.shape)
    offset = float(np.hypot(y[fy], x[fx]))
    if offset >= FOVEA_SEARCH_MM - 2 * min(spacing):
        notes.append("Thinnest point lies at the edge of the fovea search window; the grid may be decentred.")
    radius = np.hypot(yy - y[fy], xx - x[fx])

    layers = {"thickness": total}
    top, bottom = _first(named, "RNFL", "RNFL/GCL"), _first(named, "IPL", "IPL/INL")
    if top and bottom:
        layers["gcipl"] = (pixels[named[bottom]] - pixels[named[top]]) * axial
    values, scores, sentences = [], [], []
    boundary = "ILM-BM" if outer == "BM" else "ILM-RPE"
    reference = NORMS.get((device, boundary))
    for layer, grid in layers.items():
        for name, inner, outer_r in REGIONS:
            if layer == "gcipl" and name == "center":
                continue
            ring = (radius >= inner) & (radius < outer_r)
            full_area = np.pi * (outer_r ** 2 - inner ** 2)
            coverage = ring.sum() * spacing[0] * spacing[1] / full_area
            cell = grid[ring]
            if coverage < MIN_COVERAGE or np.isnan(cell).mean() > 0.2:
                notes.append(f"{layer} {name}: region not covered by the scan or unsegmented; omitted.")
                continue
            mean = float(np.nanmean(cell))
            label = f"{layer}_{name}_um"
            values.append(dict(label=label, value=round(mean, 1), unit="um"))
            norm = reference.get(name) if reference and layer == "thickness" else None
            if norm:
                z = (mean - norm[0]) / norm[1]
                flag = "below" if z < -2 else "above" if z > 2 else "within"
                scores.append(dict(label=f"{layer}_{name}_z", value=round(z, 2)))
                sentences.append(f"{name} {mean:.0f} um ({flag} norm {norm[0]:.0f}+-{norm[1]:.0f}, z {z:+.1f})")
            elif layer == "thickness":
                sentences.append(f"{name} {mean:.0f} um (no published norm for this device)")
    if not values:
        raise Degraded("no ETDRS region is covered by the scan")
    values.append(dict(label="fovea_offset_mm", value=round(offset, 3), unit="mm"))
    summary = f"Total retinal thickness ({boundary}, {acquisition.get('model')}): " + "; ".join(sentences) + "."
    if reference:
        summary += f" Reference: {reference['source']} (unreviewed)."
    notes.append(f"Axial {axial} um per A-scan pixel for {acquisition.get('model')}; lateral {spacing[0]:.4f} x {spacing[1]:.4f} mm.")
    return [labels(values, "physical"), labels(scores, "score"), text(summary)]
