"""Device constants and published normative values. Every number carries its source."""

# Axial size of one A-scan pixel in micrometres, per device model (matched as a lowercase substring
# of ManufacturerModelName). Source: PixelSpacing[0] of the same devices' structural OCT DICOMs in
# AI-READI (retinal_oct/manifest.tsv); Triton varies 2.564-2.586 by instrument (each unit carries its
# own calibration; FDA 510(k) K173119), the midpoint is used (<0.5% error). Manufacturer
# specifications agree: Spectralis 3.9, Maestro2 2.6 +-2%, Triton 2.6, Cirrus 5000 2.0 mm / 1024.
AXIAL_UM = {"spectralis": 3.872, "maestro2": 2.6, "triton": 2.575, "cirrus": 1.953125}

# (device, boundary) -> {region: (mean_um, sd_um), 'source': citation}. Healthy adults, ETDRS grid.
# Where a study reports the four ring sectors only, the ring mean is the mean of the sectors and the
# SD is the mean sector SD (conservative: a ring average varies less than one sector).
# Only references whose device family and outer boundary match what the adapter measures are used.
NORMS = {
    ("spectralis", "ILM-BM"): {
        "center": (264.0, 22.0), "inner": (333.5, 16.5), "outer": (293.5, 14.5),
        "source": "Aghamirsalim M et al., Sci Rep 2026;16:21144, Table 1 (Spectralis, ILM-BM, n=2205, age 50-74; rings from sectors)",
    },
    ("cirrus", "ILM-RPE"): {
        "center": (265.9, 21.4), "inner": (321.2, 14.7), "outer": (273.5, 12.9),
        "source": "von Hanno T et al., Acta Ophthalmol 2017;95:262-269, Table 3 (Cirrus, ILM-RPE, Tromso, n=4508, age 38-87)",
    },
    # Topcon 3D OCT-1000 Mk II, ILM-BM, applied to Maestro2 and Triton (same vendor, same boundary,
    # other instrument and software generation). Topcon's own Triton database (FDA K173119) does not
    # state its outer boundary, and ILM-RPE vs ILM-BM differs by about 25 um, so it is not used.
    ("maestro2", "ILM-BM"): {
        "center": (285.4, 22.3), "inner": (334.5, 15.9), "outer": (289.7, 13.6),
        "source": "Myers CE et al., Am J Ophthalmol 2015;159:445-456, Tables 2-3 (Topcon 3D OCT-1000, ILM-BM, Beaver Dam, n=977, age 63-85+)",
    },
    ("triton", "ILM-BM"): {
        "center": (285.4, 22.3), "inner": (334.5, 15.9), "outer": (289.7, 13.6),
        "source": "Myers CE et al., Am J Ophthalmol 2015;159:445-456, Tables 2-3 (Topcon 3D OCT-1000, ILM-BM, Beaver Dam, n=977, age 63-85+)",
    },
}
