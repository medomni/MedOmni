import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

PERCEPTION = Path(__file__).resolve().parents[2] / "perception"

from ._runtime import contract  # noqa: E402

HAS_WFDB = importlib.util.find_spec("numpy") and importlib.util.find_spec("wfdb")
FIXTURES = (PERCEPTION / "encoders"
            / "ecg-12lead-500hz-mv" / "ecgfounder" / "testdata")


@unittest.skipUnless(HAS_WFDB, "numpy and wfdb are required")
class WfdbDecoderTests(unittest.TestCase):
    def test_real_record_matches_the_family(self):
        sample = contract.read_family(
            "ecg-12lead-500hz-mv", FIXTURES / "input-ptbxl-00057.hea", FIXTURES)

        self.assertEqual(list(contract._ECG_12LEAD_CHANNELS), sample["order"])
        self.assertEqual(5000, sample["n_samples"])
        self.assertEqual(500.0, sample["rate_hz"])
        self.assertEqual("mV", sample["units"])

    def test_duplicate_family_lead_degrades(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy(FIXTURES / "ptbxl-00057.dat", root / "duplicate.dat")
            lines = (FIXTURES / "input-ptbxl-00057.hea").read_text().splitlines()
            lines[0] = "duplicate 13 500 5000"
            lines = [line.replace("ptbxl-00057.dat", "duplicate.dat") for line in lines]
            lines.insert(2, lines[1])
            header = root / "duplicate.hea"
            header.write_text("\n".join(lines) + "\n")

            with self.assertRaisesRegex(contract.Degraded, "lead more than once: I"):
                contract.read_family("ecg-12lead-500hz-mv", header, root)

    def test_signal_file_outside_data_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "data"
            root.mkdir()
            shutil.copy(FIXTURES / "ptbxl-00057.dat", parent / "outside.dat")
            (root / "outside.dat").symlink_to(parent / "outside.dat")
            lines = (FIXTURES / "input-ptbxl-00057.hea").read_text().splitlines()
            lines[0] = "escape 12 500 5000"
            lines = [line.replace("ptbxl-00057.dat", "outside.dat") for line in lines]
            header = root / "escape.hea"
            header.write_text("\n".join(lines) + "\n")

            with self.assertRaisesRegex(contract.BadRequest, "outside DATA_ROOT"):
                contract.read_family("ecg-12lead-500hz-mv", header, root)


class MeasurementDecoderTests(unittest.TestCase):
    def test_non_finite_measurements_are_not_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.jsonl"
            source.write_text('{"_t":"0","heartrate":"NaN","o2sat":"Infinity"}\n')

            sample = contract.read_family("clinical-measurement-irregular", source, root)

        self.assertEqual([], sample["rows"])
        self.assertIn("2 non-finite measurement(s) skipped", sample["notes"])


class NewFamilyTests(unittest.TestCase):
    def test_numeric_observations_reject_an_invalid_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "input.json"
            path.write_text(json.dumps({"observations": [
                {"name": "heart_rate", "value": 72, "unit": "bpm"},
                {"name": "oxygen_saturation", "value": "unknown", "unit": "%"},
            ]}))

            with self.assertRaisesRegex(contract.Degraded, "invalid"):
                contract.read_family("numeric-observation", path, root)

    def test_echo_manifest_cannot_name_a_file_outside_data_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "input.json"
            path.write_text(json.dumps({"files": ["../patient.dcm"]}))

            with self.assertRaisesRegex(contract.BadRequest, "outside DATA_ROOT"):
                contract.input_manifest("echo-study-dicom-video", path, root)

    def test_hfo_manifest_identifies_its_signal_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            signal = root / "signal.edf"
            signal.write_bytes(b"not decoded during manifest discovery")
            path = root / "input.json"
            path.write_text(json.dumps({"file": "signal.edf", "channel": "A1",
                                        "start_sec": 1.0, "end_sec": 1.1}))

            files = contract.input_manifest("ieeg-hfo-event-2khz-uv", path, root)

            self.assertEqual([path, signal.resolve()], files)


class FamilyAliasTests(unittest.TestCase):
    def test_alias_is_scoped_to_its_family(self):
        self.assertEqual(
            ("f3-a2", False),
            contract._resolve_label("eeg-scalp-1020-19ch-200hz-uv", "F3-A2"),
        )

    # v0.2's generated alias file is gone: aliases come from Core's families module (R-120), whose own
    # tests (tests/core/test_aliases.py) cover malformed alias files.


class BadInputTests(unittest.TestCase):
    """Bad input must answer 400 or degrade, never crash with a 500.

    `path: "."` and `path: ""` both resolve to DATA_ROOT itself, and a directory
    is not an input; before the fix these reached the reader and raised.
    """

    def test_resolve_path_rejects_non_files(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "sub").mkdir()
            for rel in (".", "", "sub"):
                with self.subTest(rel=rel):
                    with self.assertRaises(contract.BadRequest):
                        contract.resolve_path(rel, data_root=root)

    def test_resolve_path_accepts_a_file(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "x.jsonl").write_text("{}\n")
            self.assertEqual(
                (Path(root) / "x.jsonl").resolve(),
                contract.resolve_path("x.jsonl", data_root=root),
            )

    def test_measurements_degrade_on_non_utf8(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "bad.jsonl"
            path.write_bytes(b'{"measurement":"creatinine","value":1.0}\n\xff\xfe\x80\n')
            with self.assertRaises(contract.Degraded):
                contract._read_measurements(path, Path(root))


if __name__ == "__main__":
    unittest.main()
