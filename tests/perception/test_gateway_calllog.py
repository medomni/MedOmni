"""The call log. Bench derives budget from it, so a write that does nothing is a bug."""
import tempfile
import unittest
from pathlib import Path


from medomni.perception.gateway.calllog import CallLog


class WriteTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_call_writes_one_line(self):
        """The bug this exists to stop: write() called a helper that did not exist.

        Every write raised AttributeError, write() caught it, and the log stayed
        empty. Only the `failed` counter showed it, and nothing reads that.
        """
        with tempfile.TemporaryDirectory() as tmp:
            log = CallLog(Path(tmp) / "calls.jsonl")

            await log.write(encoder_id="e__f", path="input.hea")

            self.assertEqual(1, len(log.path.read_text().splitlines()))
            self.assertEqual(0, log.failed)

    async def test_the_line_is_json_and_carries_a_time(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            log = CallLog(Path(tmp) / "calls.jsonl")

            await log.write(encoder_id="e__f", path="input.hea", cached=False)

            record = json.loads(log.path.read_text())
            self.assertEqual("e__f", record["encoder_id"])
            self.assertIn("t", record)

    async def test_two_calls_append_rather_than_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = CallLog(Path(tmp) / "calls.jsonl")

            await log.write(encoder_id="a__b", path="one")
            await log.write(encoder_id="c__d", path="two")

            self.assertEqual(2, len(log.path.read_text().splitlines()))

    async def test_a_missing_path_disables_the_log_without_failing(self):
        log = CallLog(None)

        await log.write(encoder_id="e__f", path="input.hea")

        self.assertIsNone(log.path)
        self.assertEqual(0, log.failed)

    async def test_log_paths_false_records_a_digest_instead_of_the_path(self):
        """A request path can name a patient."""
        with tempfile.TemporaryDirectory() as tmp:
            log = CallLog(Path(tmp) / "calls.jsonl", log_paths=False)

            await log.write(encoder_id="e__f", path="patients/12345/input.hea")

            written = log.path.read_text()
            self.assertNotIn("12345", written)
            self.assertIn("sha256:", written)


if __name__ == "__main__":
    unittest.main()
