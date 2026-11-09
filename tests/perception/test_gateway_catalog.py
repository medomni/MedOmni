"""Catalog loading, search and filters. No docker, no network."""
import dataclasses
import unittest
from pathlib import Path

from ._gateway import ENCODERS, shipped, shipped_catalog

from medomni.perception.gateway.catalog import Catalog, CatalogError

ECG = "ecg-12lead-500hz-mv__ecgfounder"
CXR = "cxr-radiograph-2d__torchxrayvision"


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = shipped_catalog()

    def test_every_shipped_card_loads(self):
        self.assertEqual(set(shipped()), {e.id for e in self.catalog.all()})
        self.assertEqual(44, len(self.catalog))  # R-63

    def test_a_card_that_the_gate_would_reject_fails_the_load(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "nope" / "not-an-id"
            bad.mkdir(parents=True)
            (bad / "card.yaml").write_text("id: not-an-id\nfamily: nope\n")
            with self.assertRaises(CatalogError):
                Catalog.load(tmp)

    def test_search_ranks_the_signal_the_words_name(self):
        for query, expected in [("ecg", ECG), ("ekg", ECG), ("heart tracing", ECG),
                                ("chest xray", CXR), ("radiograph", CXR),
                                ("vital signs", "clinical-measurement-irregular__labs-summary"),
                                ("glucose", "cgm-5min-mgdl__pyagata")]:
            with self.subTest(query=query):
                found = self.catalog.search(q=query)
                self.assertTrue(found, f"{query!r} matched nothing")
                self.assertEqual(expected.split("__")[0], found[0][0].family)

    def test_search_scores_are_ordered_and_bounded(self):
        found = self.catalog.search(q="ecg embedding", runnable=None)
        scores = [score for _, score in found]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0.0 <= s <= 1.0 for s in scores))

    def test_nonsense_matches_nothing(self):
        self.assertEqual([], self.catalog.search(q="xyzzy quuxbar"))

    def test_filters_are_exact(self):
        """v0.2's expectation listed encoders that v0.3.0 does not ship (echo) and missed two it does (MIRAGE);
        the exact answer is every shipped card that declares an embedding block, in id order."""
        embedding = sorted(e.id for e in self.catalog.all() if "embedding" in e.kinds)
        self.assertEqual(embedding, [e.id for e, _ in self.catalog.search(kind="embedding")])
        self.assertEqual(["cxr-radiograph-2d__biomedclip", ECG, "ecg-1lead-200hz-uv__ecgfounder",
                          "ecg-monitor-3to5lead-250hz-continuous__ecgfounder", "fundus-photography-2d__retfound",
                          "oct-bscanset-radial24-circle3-mono8__mirage-onh", "oct-volume-raster-mono8-3d__mirage"],
                         embedding)
        self.assertEqual(["cxr-radiograph-2d__chexzero", CXR],
                         [e.id for e, _ in self.catalog.search(label="Cardiomegaly")])
        self.assertEqual([], self.catalog.search(family="no-such-family"))

    def test_card_only_encoders_are_hidden_by_default(self):
        runnable = self.catalog.get(CXR)
        source = self.catalog.get("cxr-radiograph-2d__chexzero")
        card_only = dataclasses.replace(source, runnable=False)
        catalog = Catalog([runnable, card_only])

        default = {e.id for e, _ in catalog.search(limit=50)}
        every = {e.id for e, _ in catalog.search(runnable=None, limit=50)}

        self.assertEqual({CXR}, default)
        self.assertEqual({CXR, card_only.id}, every)

    def test_the_card_is_served_unaltered(self):
        entry = self.catalog.get(CXR)
        import yaml
        on_disk = yaml.safe_load((ENCODERS / CXR.replace("__", "/", 1) / "card.yaml").read_text())
        self.assertEqual(on_disk, entry.card)


if __name__ == "__main__":
    unittest.main()
