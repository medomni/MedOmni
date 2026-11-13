"""Protect pressure units and confinement of arterial waveform companions."""
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2] / "perception"
from ._runtime import contract  # noqa: E402


class AbpTests(unittest.TestCase):
    def test_declared_rate_is_not_rounded(self):
        root=Path(__file__).resolve().parent / 'fixtures/abp-waveform-125hz-mmhg'
        sample=contract.read_family('abp-waveform-125hz-mmhg',root/'input.hea',root)
        self.assertEqual(124.945,sample['rate_hz'])
        self.assertEqual('mmHg',sample['units'])
        self.assertEqual(['input.hea','waveform.dat'],
            [p.name for p in contract.input_manifest('abp-waveform-125hz-mmhg',root/'input.hea',root)])

    def test_wrong_pressure_units_are_rejected(self):
        source=Path(__file__).resolve().parent / 'fixtures/abp-waveform-125hz-mmhg'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.hea'
            path.write_text((source/'input.hea').read_text().replace('/mmHg','/kPa'))
            shutil.copyfile(source/'waveform.dat',Path(tmp)/'waveform.dat')
            with self.assertRaises(contract.Degraded):
                contract.read_family('abp-waveform-125hz-mmhg',path,Path(tmp))

    def test_companion_cannot_escape_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.hea'
            path.write_text('sample 1 124.945 1000\n../private.dat 16 1/mmHg 16 0 0 0 0 ABP\n')
            with self.assertRaises(contract.BadRequest):
                contract.read_family('abp-waveform-125hz-mmhg',path,Path(tmp))
