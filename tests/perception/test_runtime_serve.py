import unittest
from pathlib import Path

PERCEPTION = Path(__file__).resolve().parents[2] / "perception"

from ._runtime import contract  # noqa: E402
from ._runtime import serve  # noqa: E402


class AdapterContractTests(unittest.TestCase):
    def test_family_mismatch_stops_before_encode(self):
        class WrongAdapter:
            FAMILY = "wrong-family"
            called = False

            @classmethod
            def encode(cls, sample, options):
                cls.called = True
                return []

        card = {"id": "example", "family": "right-family"}

        with self.assertRaisesRegex(RuntimeError, "adapter reads 'wrong-family'"):
            serve.run_encode(card, WrongAdapter, {})

        self.assertFalse(WrongAdapter.called)


class ContentLengthTests(unittest.TestCase):
    def test_valid_length_is_accepted(self):
        self.assertEqual(12, serve.content_length("12"))

    def test_invalid_lengths_are_caller_errors(self):
        for value in ("not-a-number", "-1", str(serve.MAX_BODY + 1)):
            with self.subTest(value=value):
                with self.assertRaises(contract.BadRequest):
                    serve.content_length(value)


if __name__ == "__main__":
    unittest.main()
