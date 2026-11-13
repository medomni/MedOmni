"""The registry: card checks, the image build command and key, response comparison, family samples. No Docker."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from medomni.perception import registry, scaffold
from medomni.perception.registry import build, cards, check

from ._gateway import ENCODERS, REPO, shipped


class CompareTests(unittest.TestCase):
    def test_tolerance_accepts_small_finite_difference(self):
        self.assertEqual([], check.compare(1.0, 1.0005, 0.001))

    def test_tolerance_rejects_nan(self):
        self.assertIn("finite numbers", check.compare(1.0, math.nan, 0.001)[0])


class ExpectedResponseTests(unittest.TestCase):
    def _load(self, text, names):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "expected.json"
            path.write_text(text)
            return check.load_expected(path, names)

    def test_empty_response_map_is_not_a_baseline(self):
        expected, errors = self._load("{}\n", {"input.png": {}})
        self.assertIsNone(expected)
        self.assertIn("no frozen responses", errors[0])

    def test_invalid_json_reports_the_file_error(self):
        expected, errors = self._load("{", {})
        self.assertIsNone(expected)
        self.assertIn("could not read testdata/expected.json", errors[0])

    def test_named_responses_match_named_inputs(self):
        expected, errors = self._load(json.dumps({"input.png": {"healthy": True}}), {"input.png": {}})
        self.assertEqual({"input.png": {"healthy": True}}, expected)
        self.assertEqual([], errors)


def _encoder(root, card=None, dockerfile=None, family="cgm-5min-mgdl", name="model"):
    edir = Path(root) / "perception/encoders" / family / name
    edir.mkdir(parents=True)
    scaffold.write(edir.parent / ("x-" + name), family, name)  # a scaffold beside, for its card text
    text = (edir.parent / ("x-" + name) / "card.yaml").read_text()
    (edir / "card.yaml").write_text(card if card is not None else text)
    (edir / "adapter.py").write_text("FAMILY = 'x'\n")
    (edir / "Dockerfile").write_text(dockerfile if dockerfile is not None else
                                     (edir.parent / ("x-" + name) / "Dockerfile").read_text())
    return edir


class CardCheckTests(unittest.TestCase):
    def test_every_shipped_folder_passes(self):
        for eid in shipped():
            with self.subTest(encoder=eid):
                errors, _ = cards.check(registry.encoder_dir(eid, ENCODERS))
                self.assertEqual([], errors)

    def test_a_scaffolded_folder_passes_with_its_todos_named(self):
        with tempfile.TemporaryDirectory() as root:
            edir = _encoder(root)
            errors, warnings = cards.check(edir)
            self.assertEqual([], errors)
            self.assertTrue(any("TODO field" in w for w in warnings))

    def test_a_dockerfile_must_run_the_shared_runtime(self):
        with tempfile.TemporaryDirectory() as root:
            edir = _encoder(root, dockerfile='FROM scratch\nCMD ["python", "/app/serve.py", "serve"]\n')
            errors, _ = cards.check(edir)
            self.assertIn("Dockerfile does not run the shared runtime (medomni.perception.runtime.serve)", errors)

    def test_the_card_contract_and_the_family_are_checked(self):
        with tempfile.TemporaryDirectory() as root:
            edir = _encoder(root, card="id: cgm-5min-mgdl__model\nfamily: cgm-5min-mgdl\n")
            errors, _ = cards.check(edir)
            self.assertTrue(any("authors" in e for e in errors), errors)  # Core's model card contract
        with tempfile.TemporaryDirectory() as root:
            edir = _encoder(root, family="no-such-family")
            errors, _ = cards.check(edir)
            self.assertTrue(any("not declared in core/families/" in e for e in errors), errors)


class BuildTests(unittest.TestCase):
    def test_the_context_is_the_repository_root(self):
        edir = registry.encoder_dir("cgm-5min-mgdl__pyagata", ENCODERS)
        cmd = build.command(edir, REPO)
        self.assertEqual(["docker", "build", "-t", "ghcr.io/medomni/cgm-5min-mgdl__pyagata:dev"], cmd[:4])
        self.assertEqual(["-f", str(edir / "Dockerfile"), str(REPO)], cmd[-3:])
        self.assertTrue(any(c.startswith("org.medomni.build_key=sha256:") for c in cmd))

    def test_stage_links_a_path_allowed_twice_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lib").mkdir()
            (root / "lib/a.py").write_text("A = 1\n")
            edir = root / "enc"
            edir.mkdir()
            (edir / "Dockerfile").write_text("FROM scratch\n")
            (edir / "Dockerfile.dockerignore").write_text("*\n!lib\n!lib/a.py\n")
            dst = build.stage(edir, root)
            self.assertEqual("A = 1\n", (dst / "lib/a.py").read_text())
            self.assertTrue((dst / "enc/Dockerfile").exists())

    def _tree(self, directory):
        """The shared runtime and one encoder, outside git, so the key uses its file walk."""
        root = Path(directory)
        for rel in build.SHARED:
            p = root / rel
            if rel.endswith(".py"):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("")
            else:
                p.mkdir(parents=True, exist_ok=True)
                (p / "x.py").write_text("A = 1\n")
        edir = root / "perception/encoders/fam/enc"
        edir.mkdir(parents=True)
        (edir / "adapter.py").write_text("x = 1\n")
        (edir / "card.yaml").write_text("id: fam__enc\nfamily: fam\n")
        return root, edir

    def test_key_is_stable_and_ignores_bytecode(self):
        with tempfile.TemporaryDirectory() as directory:
            root, edir = self._tree(directory)
            first = build.build_key(edir, root)
            (edir / "__pycache__").mkdir()
            (edir / "__pycache__" / "adapter.cpython-311.pyc").write_bytes(b"\0")
            self.assertEqual(first, build.build_key(edir, root))

    def test_runtime_and_family_changes_stale_every_encoder(self):
        with tempfile.TemporaryDirectory() as directory:
            root, edir = self._tree(directory)
            before = build.build_key(edir, root)
            (root / "src/medomni/perception/runtime/x.py").write_text("A = 2\n")
            middle = build.build_key(edir, root)
            (root / "core/families/x.py").write_text("A = 3\n")
            self.assertEqual(3, len({before, middle, build.build_key(edir, root)}))

    def test_card_pin_change_changes_the_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root, edir = self._tree(directory)
            before = build.build_key(edir, root)
            (edir / "card.yaml").write_text("id: fam__enc\nfamily: fam\nweights: {sha256: ab}\n")
            self.assertNotEqual(before, build.build_key(edir, root))


class FamilySampleTests(unittest.TestCase):
    def test_manifest_path_cannot_leave_the_sample_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.jsonl").write_text(json.dumps({"file": "../outside.edf", "sha256": "0" * 64}) + "\n")
            with self.assertRaisesRegex(RuntimeError, "escapes its directory"):
                check.manifest_entries(root)

    def test_manifest_hash_mismatch_is_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.edf").write_bytes(b"published sample")
            (root / "manifest.jsonl").write_text(json.dumps({"file": "sample.edf", "sha256": "0" * 64}) + "\n")
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                check.manifest_entries(root)

    def test_output_dimension_must_match_the_card(self):
        card = {"id": "family__model", "family": "family", "outputs": [{"kind": "embedding", "dim": 2}]}
        response = {"encoder_id": "family__model", "family": "family", "healthy": True,
                    "outputs": [{"kind": "embedding", "dim": 3, "vector": [1.0, 2.0, 3.0]}]}
        self.assertIn("embedding dimension does not match", check.family_response_problems(card, response)[0])

    def test_unhealthy_real_sample_fails_the_gate(self):
        card = {"id": "family__model", "family": "family", "outputs": []}
        response = {"encoder_id": "family__model", "family": "family", "healthy": False, "outputs": []}
        self.assertIn("did not produce healthy output", check.family_response_problems(card, response)[0])


class IndexTests(unittest.TestCase):
    def test_one_row_per_shipped_encoder(self):
        rows = registry.index.entries(ENCODERS, shipped())
        self.assertEqual(list(shipped()), [r["id"] for r in rows])
        self.assertTrue(all(r["runnable"] for r in rows))


if __name__ == "__main__":
    unittest.main()
