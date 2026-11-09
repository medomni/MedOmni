"""Container naming. The name must keep two configurations apart, or a leftover blocks them.

No docker: only name_for, tag_for and labels_for, which are pure.
"""
import tempfile
import unittest


from medomni.perception.gateway import config
from medomni.perception.gateway.runner import DockerRunner

ENCODER = "clinical-measurement-irregular__labs-summary"  # rule-vitals is not shipped (R-63)


def runner(**overrides):
    return DockerRunner(config.load(None, dict({"call_log": None}, **overrides)))


class NameTests(unittest.TestCase):
    def test_two_data_roots_get_two_names(self):
        """A leftover container for another data root must not block this one.

        Adoption refuses it, because the labels differ, and start() cannot remove
        it. Sharing the name therefore gives a 503 that never clears.
        """
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            first = runner(data_root=one).name_for(ENCODER)
            second = runner(data_root=two).name_for(ENCODER)

            self.assertNotEqual(first, second)

    def test_two_image_tags_get_two_names(self):
        """Same reason as the data root: image_tag is part of what proves ownership."""
        first = runner(image_tag="dev").name_for(ENCODER)
        second = runner(image_tag="v1").name_for(ENCODER)

        self.assertNotEqual(first, second)

    def test_the_name_covers_every_label_adoption_checks(self):
        """Whatever labels_for distinguishes, name_for must distinguish too."""
        base = runner()
        with tempfile.TemporaryDirectory() as root:
            for change in ({"image_tag": "v1"}, {"data_root": root}):
                with self.subTest(change=change):
                    other = runner(**change)
                    self.assertNotEqual(base.labels_for(ENCODER),
                                        other.labels_for(ENCODER))
                    self.assertNotEqual(base.name_for(ENCODER),
                                        other.name_for(ENCODER))

    def test_one_configuration_always_gets_the_same_name(self):
        """Adoption finds the running container by name, so the name cannot drift."""
        self.assertEqual(runner().name_for(ENCODER), runner().name_for(ENCODER))

    def test_two_encoders_get_two_names(self):
        self.assertNotEqual(runner().name_for(ENCODER),
                            runner().name_for("cgm-5min-mgdl__pyagata"))

    def test_the_name_starts_with_the_prefix_and_fits_docker(self):
        name = runner(container_prefix="medomni-gw").name_for(ENCODER)

        self.assertTrue(name.startswith("medomni-gw-"))
        self.assertLessEqual(len(name), 110)

    def test_the_digest_survives_truncation(self):
        """A long encoder id must not push the digest out of the name."""
        long_id = "f" * 120 + "__encoder"
        first = runner(image_tag="dev").name_for(long_id)
        second = runner(image_tag="v1").name_for(long_id)

        self.assertEqual(110, len(first))
        self.assertNotEqual(first, second)


class TagTests(unittest.TestCase):
    def test_the_tag_comes_from_the_deployment(self):
        self.assertTrue(runner(image_tag="v1").tag_for(ENCODER).endswith(":v1"))

    def test_the_image_label_repeats_the_tag(self):
        """The label and the started image must name one thing."""
        one = runner(image_tag="v1")
        labels = one.labels_for(ENCODER)

        self.assertEqual(one.tag_for(ENCODER), labels["org.medomni.image"])


if __name__ == "__main__":
    unittest.main()
