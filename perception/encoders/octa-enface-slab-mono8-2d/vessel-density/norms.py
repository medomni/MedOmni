"""Published normative values for OCTA metrics. Every number carries its source."""

# (device, slab) -> {metric: (mean, sd), "source": citation}. Healthy adults.
# Vessel density has no entry: every published norm uses the device's proprietary binarisation or
# skeletonisation, which an Otsu threshold on the exported slab does not reproduce.
# FAZ area: Shiihara 2018 is Triton (manual tracing, 3x3 scans, no axial-length correction stated);
# applied to Maestro2 as the same vendor and slab definition. FAZ area scales with ocular
# magnification squared, and this adapter applies no axial-length correction either.
_TOPCON_FAZ = {
    "faz_area_mm2": (0.329, 0.115),
    "source": "Shiihara H et al., Sci Rep 2018;8:10143, Table 2 (Triton SCP FAZ, manual, 3x3, n=70, age 20-61)",
}
NORMS = {("triton", "superficial"): _TOPCON_FAZ, ("maestro2", "superficial"): _TOPCON_FAZ}
