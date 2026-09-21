"""Synthetic DICOM fixture with two equal photon peaks in bins 10 and 20; Apache-2.0."""
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
pixels = np.zeros((1024, 256, 256), dtype=np.uint16)
pixels[10, :, :] = 2
pixels[20, :, :] = 2
dataset.Rows, dataset.Columns = pixels.shape[-2:]
if pixels.ndim == 3:
    dataset.NumberOfFrames = pixels.shape[0]
dataset.SamplesPerPixel = 1
dataset.PhotometricInterpretation = "MONOCHROME2"
dataset.BitsAllocated = dataset.BitsStored = 16
dataset.HighBit = 15
dataset.PixelRepresentation = 0
dataset.PixelData = pixels.tobytes()
from pydicom.uid import RLELossless
dataset.compress(RLELossless, generate_instance_uid=False)
dataset.save_as(root / "input.dcm", enforce_file_format=True)
(root / "input-empty.dcm").write_bytes(b"")
