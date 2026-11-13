import socket
import unittest
from unittest.mock import Mock, patch

from medomni.perception.gateway import runner as container  # the one Docker runner holds the lifecycle now


class _Answer:
    """The little an Encoder call reads off a urlopen response."""

    status = 200

    def read(self):
        return b'{"ok": true}'


class EncoderRequestTests(unittest.TestCase):
    def test_encode_sends_model_options(self):
        encoder = container.Encoder("http://127.0.0.1:8080")
        encoder._call = Mock(return_value=(200, {"healthy": True}))

        encoder.encode("input.hea", family="abp-waveform-125hz-mmhg",
                       options={"age_years": 53})

        encoder._call.assert_called_once_with("/encode", {
            "family": "abp-waveform-125hz-mmhg",
            "path": "input.hea",
            "options": {"age_years": 53},
        })


class EncoderTimeoutTests(unittest.TestCase):
    def test_a_call_uses_the_encoder_timeout(self):
        """The gateway sets this from deployment.encode_timeout_s.

        It was fixed at 120 s, below the 300 s a request may wait for a slot, so
        a slow encode failed and the pool removed a container that still worked.
        """
        encoder = container.Encoder("http://127.0.0.1:8080", timeout=42)
        with patch("urllib.request.urlopen") as opened:
            opened.return_value.__enter__.return_value = _Answer()

            encoder._call("/healthz")

        self.assertEqual(42, opened.call_args.kwargs["timeout"])

    def test_an_explicit_timeout_wins_over_the_encoder_one(self):
        encoder = container.Encoder("http://127.0.0.1:8080", timeout=42)
        with patch("urllib.request.urlopen") as opened:
            opened.return_value.__enter__.return_value = _Answer()

            encoder._call("/healthz", timeout=7)

        self.assertEqual(7, opened.call_args.kwargs["timeout"])


class ContainerTagTests(unittest.TestCase):
    def test_a_given_tag_is_used(self):
        """The gateway passes deployment.image_tag. It was always :dev, so Evidence
        could name one image while another ran."""
        box = container.Container("cgm-5min-mgdl__pyagata", baked=True,
                                  tag="ghcr.io/medomni/cgm-5min-mgdl__pyagata:v1")

        self.assertEqual("ghcr.io/medomni/cgm-5min-mgdl__pyagata:v1", box.tag)

    def test_without_a_tag_the_development_one_is_used(self):
        box = container.Container("cgm-5min-mgdl__pyagata", baked=True)

        self.assertTrue(box.tag.endswith(":dev"))


class PortTests(unittest.TestCase):
    def test_bound_port_is_not_available(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]

            self.assertFalse(container.port_available(port))

    def test_free_port_skips_a_bound_preference(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            occupied = listener.getsockname()[1]

            selected = container.free_port(occupied)

        self.assertNotEqual(occupied, selected)
        self.assertTrue(container.port_available(selected))

    def test_invalid_ports_are_not_available(self):
        for port in (True, "8080", 0, -1, 65536):
            with self.subTest(port=port):
                self.assertFalse(container.port_available(port))


if __name__ == "__main__":
    unittest.main()
