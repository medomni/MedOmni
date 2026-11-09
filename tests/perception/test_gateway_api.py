"""Routes and status mapping, against a fake pool. No docker.

Skipped when fastapi is absent, so the rest of the suite runs on a bare checkout.
"""
import dataclasses
import tempfile
import unittest
from pathlib import Path

from ._gateway import ENCODERS, shipped_catalog

try:
    from fastapi.testclient import TestClient
except ImportError:                                   # pragma: no cover
    raise unittest.SkipTest("fastapi is not installed")

from medomni.perception.gateway import config
from medomni.perception.gateway.app import create_app
from medomni.perception.gateway.catalog import Catalog
from medomni.perception.gateway.pool import PoolError, UpstreamError

VITALS = "clinical-measurement-irregular__labs-summary"  # rule-vitals is not shipped (R-63)
DATA = ENCODERS / VITALS.replace("__", "/", 1) / "testdata"
_LOGS = tempfile.TemporaryDirectory()  # the call log goes here, not into the working folder
CALL_LOG = str(Path(_LOGS.name) / "calls.jsonl")


class FakePool:
    """Answers like a pool that holds one healthy container."""

    def __init__(self, http_status=200, body=None, raises=None):
        self.http_status, self.raises = http_status, raises
        self.body = body
        self.calls = []

    async def encode(self, encoder_id, body):
        self.calls.append((encoder_id, body))
        if self.raises:
            raise self.raises
        answer = self.body or {"encoder_id": encoder_id, "family": body["family"],
                               "healthy": True, "outputs": [], "notes": [],
                               "runtime": {"duration_ms": 1.0}}
        return self.http_status, answer, 0.0, "sha256:fake"

    async def image_id(self, encoder_id):
        return "sha256:fake"

    async def warm(self, encoder_id):
        if self.raises:
            raise self.raises
        return 0.0

    async def evict(self, encoder_id):
        return True

    async def docker_available(self):
        return True

    def status(self):
        return []

    def start_reaper(self):
        pass

    async def stop_reaper(self):
        pass

    async def close(self):
        pass


def client(pool, catalog=None, data_root=None):
    deployment = config.load(None, {"data_root": str(data_root or DATA), "call_log": CALL_LOG,
                                    "stop_on_exit": False})
    app = create_app(deployment,
                     catalog=catalog or shipped_catalog(), pool=pool)
    return TestClient(app)


class DiscoveryTests(unittest.TestCase):
    def test_discovery_never_touches_the_pool(self):
        pool = FakePool()
        with client(pool) as api:
            self.assertEqual(200, api.get("/encoders", params={"q": "ecg"}).status_code)
            self.assertEqual(200, api.get(f"/cards/{VITALS}").status_code)
            self.assertEqual(200, api.get("/families").status_code)
        self.assertEqual([], pool.calls)

    def test_the_card_is_returned_verbatim(self):
        import yaml
        with client(FakePool()) as api:
            served = api.get(f"/cards/{VITALS}").json()
        on_disk = yaml.safe_load((ENCODERS / VITALS.replace("__", "/", 1) / "card.yaml").read_text())
        self.assertEqual(on_disk, served)

    def test_every_runnable_encoder_is_listed_without_a_limit(self):
        """A default cap answered 20 of 35 and said nothing about the 15 it left out."""
        catalog = shipped_catalog()
        runnable = [e for e in catalog.all() if e.runnable]
        self.assertGreater(len(runnable), 20)

        with client(FakePool(), catalog=catalog) as api:
            listed = api.get("/encoders").json()

        self.assertEqual(len(runnable), len(listed))

    def test_a_limit_still_narrows_the_answer(self):
        with client(FakePool()) as api:
            self.assertEqual(3, len(api.get("/encoders", params={"limit": 3}).json()))

    def test_an_unknown_encoder_is_404(self):
        with client(FakePool()) as api:
            self.assertEqual(404, api.get("/cards/nope__nope").status_code)
            self.assertEqual(404, api.post("/encode", json={"encoder_id": "nope__nope",
                                                            "path": "x"}).status_code)


class EncodeTests(unittest.TestCase):
    def body(self, **changes):
        return dict({"encoder_id": VITALS, "path": "input.jsonl"}, **changes)

    def test_the_request_carries_no_family_and_the_gateway_inserts_it(self):
        pool = FakePool()
        with client(pool) as api:
            self.assertEqual(200, api.post("/encode", json=self.body()).status_code)
        _, sent = pool.calls[0]
        self.assertEqual("clinical-measurement-irregular", sent["family"])

    def test_a_family_in_the_request_is_rejected(self):
        with client(FakePool()) as api:
            for extra in ({"family": "x"}, {"device": "cuda"}, {"replicas": 2}):
                with self.subTest(extra=list(extra)):
                    got = api.post("/encode", json=self.body(**extra))
                    self.assertEqual(422, got.status_code)

    def test_a_path_outside_the_data_root_is_400(self):
        with client(FakePool()) as api:
            for path in ("../../etc/passwd", "/etc/passwd", "no-such-file"):
                with self.subTest(path=path):
                    self.assertEqual(400, api.post("/encode",
                                                   json=self.body(path=path)).status_code)

    def test_an_input_the_family_cannot_open_is_400(self):
        """A header naming a missing .dat used to reach the caller as a 500."""
        import shutil
        import tempfile
        ecg = ENCODERS / "ecg-12lead-500hz-mv/ecgfounder/testdata"
        with tempfile.TemporaryDirectory() as root:
            shutil.copy(ecg / "input-ptbxl-00057.hea", Path(root) / "input.hea")

            with client(FakePool(), data_root=root) as api:
                got = api.post("/encode", json={"encoder_id": "ecg-12lead-500hz-mv__ecgfounder",
                                                "path": "input.hea"})

            self.assertEqual(400, got.status_code)

    def test_status_mapping(self):
        cases = [(FakePool(http_status=400, body={"error": "bad"}), 400),
                 (FakePool(http_status=500, body={"error": "boom"}), 502),
                 (FakePool(raises=UpstreamError("gone")), 502),
                 (FakePool(raises=PoolError("full")), 503)]
        for pool, expected in cases:
            with self.subTest(expected=expected):
                with client(pool) as api:
                    self.assertEqual(expected,
                                     api.post("/encode", json=self.body()).status_code)

    def test_an_answer_from_another_encoder_is_502(self):
        pool = FakePool(body={"encoder_id": "other__x", "family": "other",
                              "healthy": True, "outputs": [], "notes": [],
                              "runtime": {}})
        with client(pool) as api:
            self.assertEqual(502, api.post("/encode", json=self.body()).status_code)

    def test_a_card_only_encoder_is_409(self):
        catalog = shipped_catalog()
        card_only = dataclasses.replace(catalog.get(VITALS), runnable=False)
        with client(FakePool(), Catalog([card_only])) as api:
            got = api.post("/encode", json=self.body())
            self.assertEqual(409, got.status_code)

    def test_evidence_follows_its_contract(self):
        from medomni.core.contracts import Evidence, load_data

        with client(FakePool()) as api:
            answer = api.post("/encode", json=self.body()).json()
        load_data(answer, Evidence)  # Core's gateway API contract, not a second schema
        self.assertRegex(answer["fingerprint"], r"^sha256:[0-9a-f]{64}$")

    def test_a_repeat_is_served_from_cache(self):
        pool = FakePool()
        with client(pool) as api:
            first = api.post("/encode", json=self.body()).json()
            second = api.post("/encode", json=self.body()).json()
        self.assertEqual(1, len(pool.calls))            # the container ran once
        self.assertFalse(first["runtime"]["cached"])
        self.assertTrue(second["runtime"]["cached"])


class OperatorTests(unittest.TestCase):
    def test_the_agent_api_offers_no_pool_control(self):
        """/docs is how an agent learns what it may call. The pool is not on it."""
        with client(FakePool()) as api:
            paths = set(api.get("/openapi.json").json()["paths"])
        self.assertEqual({"/encoders", "/encoders/{encoder_id}", "/cards/{encoder_id}",
                          "/families", "/encode"}, paths)

    def test_operator_routes_answer_but_are_unlisted(self):
        with client(FakePool()) as api:
            self.assertTrue(api.get("/healthz").json()["ok"])
            self.assertTrue(api.get("/readyz").json()["ready"])
            self.assertEqual(200, api.get("/admin/pool").status_code)
            self.assertEqual(200, api.post(f"/admin/pool/{VITALS}/warm").status_code)
            self.assertEqual(200, api.delete(f"/admin/pool/{VITALS}").status_code)

    def test_admin_api_false_removes_pool_control(self):
        deployment = config.load(None, {"data_root": str(DATA), "call_log": CALL_LOG,
                                        "stop_on_exit": False, "admin_api": False})
        app = create_app(deployment, catalog=shipped_catalog(),
                         pool=FakePool())
        with TestClient(app) as api:
            self.assertEqual(404, api.get("/admin/pool").status_code)
            self.assertTrue(api.get("/readyz").json()["ready"])   # readiness stays


if __name__ == "__main__":
    unittest.main()
