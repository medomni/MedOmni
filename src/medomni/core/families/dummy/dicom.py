"""DICOM images, volumes and video, and PNG images, at the format level (R-73).

Family files declare no pixel sizes, so each family keeps its shape on a small grid that fits 1 MiB. Pixels are
seeded structure, not anatomy. The SOP class is the one such files carry; not every module of the IOD is filled.
"""
from __future__ import annotations

from pathlib import Path

from . import rng

OP8, OP16, OPT = "1.2.840.10008.5.1.4.1.1.77.1.5.1", "1.2.840.10008.5.1.4.1.1.77.1.5.2", "1.2.840.10008.5.1.4.1.1.77.1.5.4"
US, US_MULTI, PMAP = "1.2.840.10008.5.1.4.1.1.6.1", "1.2.840.10008.5.1.4.1.1.3.1", "1.2.840.10008.5.1.4.1.1.30"
SC = "1.2.840.10008.5.1.4.1.1.7"

# family -> (SOP class, modality, rows, columns, frames, samples per pixel)
GRID = {
    "fundus-photography-2d": (OP8, "OP", 128, 128, 1, 3),
    "fundus-faf-mono8-2d": (OP8, "OP", 128, 128, 1, 1),
    "octa-enface-slab-mono8-2d": (OP8, "OP", 128, 128, 1, 1),
    "oct-volume-raster-mono8-3d": (OPT, "OPT", 64, 64, 16, 1),  # parallel B-scans
    "oct-bscanset-radial24-circle3-mono8": (OPT, "OPT", 64, 64, 27, 1),  # 24 radial lines + 3 circles
    "octa-flowcube-mono8-3d": (OPT, "OPT", 64, 64, 16, 1),
    "flio-tcspc-256x256x1024bin-u16": (OP16, "OP", 8, 8, 2 * 1024, 1),  # 2 bands x 1024 time bins, on 8x8 pixels
    "retinal-heightmap-surfaces-f32": (PMAP, "OPT", 64, 64, 4, 1),  # 4 surfaces
    "echo-ultrasound-frame-2d": (US, "US", 64, 64, 1, 3),
    "echo-study-dicom-video": (US_MULTI, "US", 48, 48, 16, 3),
}
PNG_GRID = {"cxr-radiograph-2d": (128, 128)}


def _pixels(family, seed: int, shape: tuple[int, ...], dtype: str):
    import numpy as np

    g = rng(seed, family.id)
    rows, cols = shape[-3:-1] if len(shape) >= 3 and shape[-1] == 3 else shape[-2:]
    yy, xx = np.mgrid[0:rows, 0:cols]
    base = 0.5 + 0.25 * np.sin(xx / max(cols, 1) * 6.28 * g.uniform(1, 3)) * np.cos(yy / max(rows, 1) * 6.28)
    x = np.broadcast_to(base[..., None] if shape[-1] == 3 and len(shape) >= 3 else base, shape)
    x = np.clip(x + 0.1 * g.standard_normal(shape), 0, 1)
    if dtype == "float32":
        return (x * 500).astype("<f4")  # depth in micrometres
    top = 255 if dtype == "uint8" else 4095
    return (x * top).astype(np.uint8 if dtype == "uint8" else np.uint16)


def write_dicom(family, seed: int, path: Path, *, subject: str, start) -> None:
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    sop, modality, rows, cols, frames, spp = GRID[family.id]
    dtype = family.protocol.dtype
    shape = ((frames,) if frames > 1 else ()) + (rows, cols) + ((spp,) if spp > 1 else ())
    arr = _pixels(family, seed, shape, dtype)
    uid = lambda kind: generate_uid(entropy_srcs=[family.id, subject, str(seed), kind])  # noqa: E731
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = sop
    meta.MediaStorageSOPInstanceUID = uid("instance")
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = Dataset()
    ds.file_meta = meta
    ds.SOPClassUID, ds.SOPInstanceUID = sop, meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID, ds.SeriesInstanceUID = uid("study"), uid("series")
    ds.PatientID, ds.PatientName = subject, subject
    ds.Modality = modality
    ds.StudyDate = ds.ContentDate = start.strftime("%Y%m%d")
    ds.StudyTime = ds.ContentTime = start.strftime("%H%M%S")
    ds.AcquisitionDateTime = start.strftime("%Y%m%d%H%M%S")
    ds.Rows, ds.Columns, ds.SamplesPerPixel = rows, cols, spp
    ds.PhotometricInterpretation = "RGB" if spp == 3 else "MONOCHROME2"
    if spp == 3:
        ds.PlanarConfiguration = 0
    if frames > 1:
        ds.NumberOfFrames = frames
    if dtype == "float32":
        ds.BitsAllocated = 32
        ds.FloatPixelData = arr.tobytes()
    else:
        bits = 8 if dtype == "uint8" else 16
        ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = bits, bits, bits - 1, 0
        ds.PixelData = arr.tobytes()
    ds.save_as(str(path), enforce_file_format=True)


def write_png(family, seed: int, path: Path, *, subject: str, start) -> None:
    from PIL import Image

    rows, cols = PNG_GRID[family.id]
    Image.fromarray(_pixels(family, seed, (rows, cols), "uint8"), mode="L").save(path, optimize=False)
