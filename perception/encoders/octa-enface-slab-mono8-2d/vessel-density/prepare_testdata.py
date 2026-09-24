"""Synthetic OCTA en-face fixtures with a known FAZ; no patient data; Apache-2.0.

A 6 x 6 mm superficial slab (300 x 300, 0.02 mm) of seeded capillary-like texture with a dark
circular FAZ of radius 0.3 mm (area 0.2827 mm2) at the scan centre.
"""
from pathlib import Path
import numpy as np
from pydicom.dataset import FileDataset, FileMetaDataset, Dataset
from pydicom.uid import ExplicitVRLittleEndian
from scipy import ndimage

ROOT = Path(__file__).parent / "testdata"
N, SPACING, R = 300, 0.02, 0.3
rng = np.random.default_rng(7)
texture = ndimage.gaussian_filter(rng.random((N, N)), 1.0)
texture = (texture - texture.min()) / np.ptp(texture)
image = 40 + 180 * texture
yy, xx = np.meshgrid((np.arange(N) - (N - 1) / 2) * SPACING, (np.arange(N) - (N - 1) / 2) * SPACING, indexing="ij")
image[np.hypot(yy, xx) < R] = 8
PIXELS = np.clip(image, 0, 255).astype(np.uint8)


def write(name, protocol, comments, structure):
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.77.1.5.7"
    meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.10.999.8." + str(len(name))
    ds = FileDataset(str(ROOT / name), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID, ds.SOPInstanceUID = meta.MediaStorageSOPClassUID, meta.MediaStorageSOPInstanceUID
    ds.PatientName, ds.PatientID = "Synthetic", "SYNTHETIC"
    ds.Manufacturer, ds.ManufacturerModelName, ds.ProtocolName = "Topcon", "Triton plus", protocol
    if comments:
        ds.ImageComments = comments
    if structure:
        item = Dataset(); item.CodeValue, item.CodingSchemeDesignator, item.CodeMeaning = "67046006", "SCT", structure
        ds.PrimaryAnatomicStructureSequence = [item]
    ds.PixelSpacing = [SPACING, SPACING]
    ds.Rows, ds.Columns = PIXELS.shape
    ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 8, 8, 7, 0
    ds.PixelData = PIXELS.tobytes()
    ds.save_as(ROOT / name, enforce_file_format=True)


write("input.dcm", "synthetic macula 6x6 octa", "Superficial, ILM+0, IPL/INL+15.6", "Fovea centralis")
write("input-unidentified.dcm", "synthetic macula 6x6 octa", None, None)
write("input-disc.dcm", "synthetic ONH-Angiography 6x6 mm", None, None)
write("input-unknown.dcm", "synthetic 6x6 angiography", None, None)
