"""Protect waveform timing and WFDB companion confinement."""
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "perception"
from ._runtime import contract  # noqa: E402


class PpgDecoderTests(unittest.TestCase):
    def test_edf_and_wfdb_keep_the_same_samples_and_rate(self):
        root = ROOT / 'encoders/ppg-waveform-uncal/neurokit2/testdata'
        edf = contract.read_family('ppg-waveform-uncal', root/'input.edf', root)
        wfdb = contract.read_family('ppg-waveform-uncal', root/'input.hea', root)
        self.assertEqual(125, edf['rate_hz'])
        self.assertEqual(edf['rate_hz'], wfdb['rate_hz'])
        self.assertEqual(7500, edf['n_samples'])
        np.testing.assert_allclose(edf['channels']['pleth'], wfdb['channels']['pleth'], atol=3e-5)
        self.assertEqual(['input.hea', 'bidmc.dat'],
            [p.name for p in contract.input_manifest('ppg-waveform-uncal', root/'input.hea', root)])

    def test_wfdb_companion_cannot_escape_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'input.hea')
            path.write_text('sample 1 125 7500\n../outside.dat 16 1/NU 16 0 0 0 0 Pleth\n')
            with self.assertRaises(contract.BadRequest):
                contract.read_family('ppg-waveform-uncal', path, tmp)
