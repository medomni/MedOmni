"""Synthetic heightmap fixtures with known geometry; no patient data; Apache-2.0.

A 6 x 6 mm macula (121 x 121 points, 0.05 mm) with a Gaussian foveal pit at the scan centre.
Depth is in A-scan pixels. Outer surfaces are flat; the ILM dips by 23 px at the pit centre and
inner surfaces never lie above it. At the Spectralis axial size (3.872 um) the retina is 75 px =
290.4 um thick away from the fovea and 52 px = 201.3 um at the pit centre; the GCL+IPL (RNFL to
IPL boundary) is 20 px = 77.44 um away from the fovea.
"""
from pathlib import Path
import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian

ROOT = Path(__file__).parent / "testdata"
N, SPACING = 121, 0.05
r = np.hypot(*np.meshgrid((np.arange(N) - 60) * SPACING, (np.arange(N) - 60) * SPACING, indexing="ij"))
ILM = 100 + 23 * np.exp(-r ** 2 / (2 * 0.35 ** 2))
# depth below the ILM of each Spectralis surface, in pixels (ILM itself 0, BM 75)
SPECTRALIS = {"ILM": 0, "BM": 75, "RNFL": 8, "GCL": 18, "IPL": 28, "INL": 38, "OPL": 44,
              "ELM": 55, "PR1": 61, "PR2": 66, "RPE": 72}
TOPCON = ["ILM", "RNFL/GCL", "GCL", "IPL/INL", "IS/OS", "OS/RPE", "BM", "OPL", "ELM"]
TOPCON_DEPTH = [0, 8, 18, 28, 44, 55, 61, 72, 75]   # frames stored shallow to deep, labels as Topcon exports them


def write(name, labels, offsets, model, maker, protocol):
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.66.8"
    meta.MediaStorageSOPInstanceUID = f"1.2.826.0.1.3680043.10.999.{abs(hash(name)) % 10**8}"
    ds = FileDataset(str(ROOT / name), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID, ds.SOPInstanceUID = meta.MediaStorageSOPClassUID, "1.2.826.0.1.3680043.10.999.7." + str(len(name))
    ds.PatientName, ds.PatientID = "Synthetic", "SYNTHETIC"
    ds.Manufacturer, ds.ManufacturerModelName, ds.ProtocolName = maker, model, protocol
    pixels = np.stack([ILM if o == 0 else np.maximum(100.0 + o, ILM) for o in offsets]).astype(np.float32)
    ds.Rows, ds.Columns, ds.NumberOfFrames = N, N, len(offsets)
    ds.SamplesPerPixel, ds.PhotometricInterpretation, ds.BitsAllocated = 1, "MONOCHROME2", 32
    segments = []
    for number, label in enumerate(labels, 1):
        item = Dataset(); item.SegmentNumber, item.SegmentLabel = number, label; segments.append(item)
    ds.SegmentSequence = segments
    frames = []
    for number in range(1, len(labels) + 1):
        ref = Dataset(); ref.ReferencedSegmentNumber = number
        group = Dataset(); group.SegmentIdentificationSequence = [ref]; frames.append(group)
    ds.PerFrameFunctionalGroupsSequence = frames
    measures = Dataset(); measures.PixelSpacing = [SPACING, SPACING]
    shared = Dataset(); shared.PixelMeasuresSequence = [measures]
    ds.SharedFunctionalGroupsSequence = [shared]
    ds.FloatPixelData = pixels.tobytes()
    ds.save_as(ROOT / name, enforce_file_format=True)


write("input.dcm", list(SPECTRALIS), list(SPECTRALIS.values()), "SPECTRALIS", "Heidelberg Engineering", "synthetic mac 20x20")
write("input-topcon.dcm", TOPCON, TOPCON_DEPTH, "Maestro2", "Topcon", "synthetic macula 6x6")
write("input-disc.dcm", list(SPECTRALIS), list(SPECTRALIS.values()), "SPECTRALIS", "Heidelberg Engineering", "synthetic ONH 6x6")
(ROOT / "input-empty.dcm").write_bytes(b"")
