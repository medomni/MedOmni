"""Synthetic DICOM fixture with known equal populations at 0 and 100; Apache-2.0."""
from pathlib import Path
import numpy as np
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage

root = Path(__file__).parent / "testdata"
meta = FileMetaDataset()
meta.TransferSyntaxUID = ExplicitVRLittleEndian
meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.10.999.1"
dataset = FileDataset(str(root / "input.dcm"), {}, file_meta=meta, preamble=b"\0"*128)
dataset.SOPClassUID = meta.MediaStorageSOPClassUID
dataset.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
dataset.PatientName = "Synthetic"
dataset.PatientID = "SYNTHETIC"
pixels = np.zeros((2, 4, 4), dtype=np.float32)
pixels[..., 1::2] = 100
dataset.Rows, dataset.Columns = pixels.shape[-2:]
if pixels.ndim == 3:
    dataset.NumberOfFrames = pixels.shape[0]
dataset.SamplesPerPixel = 1
dataset.PhotometricInterpretation = "MONOCHROME2"
dataset.BitsAllocated = 32
dataset.FloatPixelData = pixels.tobytes()
dataset.save_as(root / "input.dcm", enforce_file_format=True)
(root / "input-empty.dcm").write_bytes(b"")
