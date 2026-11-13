"""Check missing-sample denominators and reject misleading CGM units."""
import json
import tempfile
import unittest
from pathlib import Path

PERCEPTION = Path(__file__).resolve().parents[2] / "perception"
from ._runtime import contract  # noqa: E402


class CgmTests(unittest.TestCase):
    def test_missing_slot_is_nan_and_timezone_is_normalized(self):
        path = PERCEPTION / 'encoders/cgm-5min-mgdl/pyagata/testdata/input.json'
        sample = contract.read_family('cgm-5min-mgdl', path)
        self.assertEqual([60., 70., 180., 200.], [v for v in sample['glucose'] if v == v])
        self.assertNotEqual(sample['glucose'][2], sample['glucose'][2])
        self.assertEqual(1200, (sample['times'][-1] - sample['times'][0]).total_seconds())

    def test_wrong_units_and_off_grid_times_are_rejected(self):
        path = PERCEPTION / 'encoders/cgm-5min-mgdl/pyagata/testdata/input.json'
        for field in ('unit', 'time'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                records = json.loads(path.read_text())
                if field == 'unit':
                    records[0]['body']['blood_glucose']['unit'] = 'mmol/L'
                else:
                    records[0]['body']['effective_time_frame']['date_time'] = '2024-01-01T00:01:00Z'
                modified = Path(tmp, 'input.json')
                modified.write_text(json.dumps(records))
                with self.assertRaises(contract.Degraded):
                    contract.read_family('cgm-5min-mgdl', modified)
