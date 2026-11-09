"""Check colour-plane identity and reject unsupported fundus pixel depth."""
import tempfile
import unittest
from pathlib import Path
import pydicom
from pydicom.data import get_testdata_file

ROOT = Path(__file__).resolve().parents[2] / "perception"
from ._runtime import contract  # noqa: E402
DATA = ROOT/'encoders/fundus-photography-2d/retfound/testdata'


class FundusDecoderTests(unittest.TestCase):
    def test_colour_and_monochrome_remain_distinct(self):
        colour = contract.read_family('fundus-photography-2d', DATA/'input.dcm')
        mono = contract.read_family('fundus-photography-2d', DATA/'input-monochrome.dcm')
        self.assertEqual(('colour-3plane', (512,512,3)), (colour['role'], colour['pixels'].shape))
        self.assertEqual(('infrared-1plane', (256,256)), (mono['role'], mono['pixels'].shape))

    def test_sixteen_bit_input_is_not_silently_scaled(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = pydicom.dcmread(DATA/'input.dcm')
            dataset.BitsAllocated = dataset.BitsStored = 16
            dataset.HighBit = 15
            path = Path(tmp,'input.dcm')
            dataset.save_as(path)
            with self.assertRaisesRegex(contract.Degraded, 'eight-bit'):
                contract.read_family('fundus-photography-2d', path)

    def test_ybr_full_422_is_decoded_as_colour(self):
        path = get_testdata_file('SC_ybr_full_422_uncompressed.dcm', download=False)
        self.assertIsNotNone(path)
        sample = contract.read_family('fundus-photography-2d', Path(path))
        self.assertEqual(('colour-3plane', (100, 100, 3)),
                         (sample['role'], sample['pixels'].shape))
        self.assertEqual(['DICOM YBR_FULL_422 pixels were converted to RGB'],
                         sample['notes'])
