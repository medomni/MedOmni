"""Input identity, the fingerprint, and Evidence composition."""
import shutil
import tempfile
import unittest
from pathlib import Path

from ._gateway import ENCODERS

from medomni.perception.gateway import evidence as ev
from medomni.perception.gateway.cache import Cache

ECG_DATA = ENCODERS / "ecg-12lead-500hz-mv" / "ecgfounder" / "testdata"
CARD = {"id": "e__f", "family": "f", "weights": {"sha256": "w"},
        "source": {"rev": "r"}, "runtime": {"image": "img"},
        "reliability": {"status": "unmeasured"}}
BLOCK = {"kind": "labels", "scale": "score", "items": [{"label": "a", "value": 0.5}]}
RESPONSE = {"encoder_id": "e__f", "family": "f", "healthy": True,
            "outputs": [BLOCK], "notes": [], "runtime": {"duration_ms": 1.0}}


class PathTests(unittest.TestCase):
    def test_a_path_is_confined_to_the_data_root(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "ok.txt").write_text("x")
            self.assertTrue(ev.resolve_input(root, "ok.txt").is_file())
            for bad in ("../etc/passwd", "/etc/passwd", "missing.txt", ""):
                with self.subTest(path=bad):
                    with self.assertRaises(ev.BadPath):
                        ev.resolve_input(root, bad)

    def test_a_symlink_out_of_the_root_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            outside = Path(root).parent / "outside.txt"
            outside.write_text("x")
            try:
                (Path(root) / "link.txt").symlink_to(outside)
                with self.assertRaises(ev.BadPath):
                    ev.resolve_input(root, "link.txt")
            finally:
                outside.unlink()


class IdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_wfdb_record_is_identified_by_every_file_it_names(self):
        """The bug this exists to stop: .hea unchanged, .dat changed, same key."""
        with tempfile.TemporaryDirectory() as root:
            for name in ("input-ptbxl-00057.hea", "ptbxl-00057.dat"):
                shutil.copy(ECG_DATA / name, Path(root) / name)
            header = Path(root) / "input-ptbxl-00057.hea"

            before = await ev.input_identity("ecg-12lead-500hz-mv", header, root)
            signal = Path(root) / "ptbxl-00057.dat"
            signal.write_bytes(b"\x01\x02" + signal.read_bytes()[2:])
            after = await ev.input_identity("ecg-12lead-500hz-mv", header, root)

            self.assertIsNotNone(before)
            self.assertNotEqual(before, after)

    async def test_a_family_that_cannot_say_yields_no_identity(self):
        with tempfile.TemporaryDirectory() as root:
            sample = Path(root) / "x.bin"
            sample.write_bytes(b"x")
            self.assertIsNone(await ev.input_identity("no-such-family", sample, root))

    async def test_a_header_naming_a_missing_signal_file_is_a_bad_path(self):
        """The caller named the input, so this is a bad request and not a 500.

        The header lists the .dat files. Reading them is what identity means, so
        a missing one arrives here as FileNotFoundError.
        """
        with tempfile.TemporaryDirectory() as root:
            shutil.copy(ECG_DATA / "input-ptbxl-00057.hea", Path(root) / "input.hea")
            header = Path(root) / "input.hea"

            with self.assertRaises(ev.BadPath):
                await ev.input_identity("ecg-12lead-500hz-mv", header, root)

    async def test_an_undecodable_header_is_a_bad_path(self):
        with tempfile.TemporaryDirectory() as root:
            header = Path(root) / "input.hea"
            header.write_bytes(b"\xff\xfe\x00 not a header")

            with self.assertRaises(ev.BadPath):
                await ev.input_identity("ecg-12lead-500hz-mv", header, root)

    async def test_a_directory_where_a_signal_file_belongs_is_a_bad_path(self):
        with tempfile.TemporaryDirectory() as root:
            shutil.copy(ECG_DATA / "input-ptbxl-00057.hea", Path(root) / "input.hea")
            (Path(root) / "ptbxl-00057.dat").mkdir()

            with self.assertRaises(ev.BadPath):
                await ev.input_identity("ecg-12lead-500hz-mv", Path(root) / "input.hea", root)


class FingerprintTests(unittest.TestCase):
    def key(self, **changes):
        base = {"card": CARD, "input_sha256": "abc", "path": "p",
                "image_id": "sha256:img1", "options": {}}
        base.update(changes)
        return ev.fingerprint(**base)

    def test_it_is_stable(self):
        self.assertEqual(self.key(), self.key())

    def test_it_moves_when_anything_it_claims_to_cover_moves(self):
        for change in ({"input_sha256": "def"}, {"image_id": "sha256:img2"},
                       {"options": {"n": 1}},
                       {"card": dict(CARD, weights={"sha256": "w2"})},
                       {"card": dict(CARD, source={"rev": "r2"})}):
            with self.subTest(change=list(change)):
                self.assertNotEqual(self.key(), self.key(**change))

    def test_an_unidentified_input_still_separates_by_name(self):
        a = self.key(input_sha256=None, path="one")
        b = self.key(input_sha256=None, path="two")
        self.assertNotEqual(a, b)


class ComposeTests(unittest.TestCase):
    def test_the_card_is_copied_and_the_outputs_are_not_touched(self):
        answer = ev.compose(CARD, RESPONSE, "sha256:f", "abc", "sha256:img", 12.0)
        self.assertEqual(CARD, answer["card"])
        self.assertEqual(RESPONSE["outputs"], answer["outputs"])
        self.assertIs(BLOCK, answer["outputs"][0])      # not rebuilt, not reinterpreted
        self.assertEqual(12.0, answer["runtime"]["container_start_ms"])
        self.assertTrue(answer["provenance"]["input_complete"])

    def test_an_unidentified_input_is_marked_incomplete(self):
        answer = ev.compose(CARD, RESPONSE, "sha256:f", None, "sha256:img")
        self.assertFalse(answer["provenance"]["input_complete"])

    def test_an_answer_from_another_encoder_is_refused(self):
        for wrong in ({"encoder_id": "other__x"}, {"family": "other"}):
            with self.subTest(wrong=list(wrong)):
                with self.assertRaises(ev.IdentityMismatch):
                    ev.compose(CARD, dict(RESPONSE, **wrong), "f", "abc", "img")


class CacheTests(unittest.TestCase):
    def test_it_evicts_by_bytes(self):
        cache = Cache(max_bytes=200)
        for i in range(20):
            cache.put(f"k{i}", {"payload": "x" * 50})
        self.assertLessEqual(cache.stats()["bytes"], 200)
        self.assertIsNone(cache.get("k0"))
        self.assertIsNotNone(cache.get("k19"))

    def test_zero_disables_it(self):
        cache = Cache(max_bytes=0)
        cache.put("k", {"a": 1})
        self.assertIsNone(cache.get("k"))

    def test_an_entry_larger_than_the_budget_is_not_stored(self):
        cache = Cache(max_bytes=10)
        cache.put("k", {"payload": "x" * 1000})
        self.assertIsNone(cache.get("k"))


if __name__ == "__main__":
    unittest.main()
