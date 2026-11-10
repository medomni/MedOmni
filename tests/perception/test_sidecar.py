"""The perception service (R-147), offline: guard rules, the deployment record, scoping, /usage, the image handle.

Ported from v0.2's harness/tests/test_sidecar_guard.py and the record half of test_encoder_images.py, plus what the
v0.3 port adds. Synthetic inventory, limits, records and files only; a fake pool stands in for Docker.
"""
from __future__ import annotations

import glob
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from medomni.perception import sidecar
from medomni.perception.gateway import config
from medomni.perception.sidecar import record, service
from medomni.perception.sidecar.guard import Guard, Witness, summarize_outputs

from ._gateway import ENCODERS, REPO, shipped_catalog

INV = {"families": {"ecg-1lead-200hz-uv": {
    "kind": "signal", "paths": ["files/s/night.edf", "files/s/short.edf", "files/s/nometa.edf"],
    "meta": {"files/s/night.edf": {"duration_s": 21600, "n_channels": 1, "sample_rate": [200]},
             "files/s/short.edf": {"duration_s": 600, "n_channels": 1, "sample_rate": [200]},
             "files/s/nometa.edf": None}}}}
LIM = {"ecg__nk": {"family": "ecg-1lead-200hz-uv", "min_duration_s": 30, "max_duration_s": 1800,
                   "sample_rate_hz": 200, "quote": ["Requires 30 seconds to 30 minutes ... at 200 Hz"]},
       "ecg__free": {"family": "ecg-1lead-200hz-uv", "limits": "none", "quote": []}}


# ---------------------------------------------------------------- budget and breaker

def test_budget_every_call_counts():
    g = Guard(max_calls=300, limits=LIM, inventory=INV)
    for i in range(300):
        assert g.admit("ecg__nk") is None
        g.record("ecg__nk", "files/s/night.edf", ["healthy", "bad_request", "unhealthy"][i % 3])
    assert g.admit("ecg__nk")[:2] == ("budget", 429)


def test_control_300_calls_pass():
    g = Guard(max_calls=300)
    assert all(g.admit("x") is None for _ in range(300))


def test_breaker_undeclared_failures_trip():
    g = Guard(break_after=10, limits=LIM, inventory=INV)
    for _ in range(11):  # in-limit file: a refusal is NOT declared
        g.admit("ecg__nk")
        g.record("ecg__nk", "files/s/short.edf", "unhealthy")
    assert g.admit("ecg__nk")[:2] == ("breaker", 503)
    assert "ecg__nk" in g.state()["breaker"]


def test_control_declared_refusals_do_not_trip():
    g = Guard(break_after=10, limits=LIM, inventory=INV)
    for _ in range(11):  # 6-h night vs a 30-min cap: declared, verified from the file's meta
        g.admit("ecg__nk")
        assert "not_applicable" in g.record("ecg__nk", "files/s/night.edf", "unhealthy")
    assert g.admit("ecg__nk") is None
    assert g.record("ecg__nk", "files/s/short.edf", "healthy") == {"outcome": "healthy"}


def test_the_encoders_word_is_not_taken():
    """A 'too long' refusal on an in-limit file is an undeclared failure."""
    g = Guard(limits=LIM, inventory=INV)
    assert "not_applicable" not in g.record("ecg__nk", "files/s/short.edf", "error")


def test_no_meta_or_no_limit_is_never_declared():
    g = Guard(limits=LIM, inventory=INV)
    assert "not_applicable" not in g.record("ecg__nk", "files/s/nometa.edf", "error")
    assert "not_applicable" not in g.record("ecg__free", "files/s/night.edf", "error")


def test_bad_requests_never_count():
    g = Guard(break_after=10, limits=LIM, inventory=INV)
    for _ in range(50):
        g.admit("ecg__nk")
        g.record("ecg__nk", "nope.edf", "bad_request")
    assert g.admit("ecg__nk") is None


def test_healthy_resets_the_run():
    g = Guard(break_after=10, limits=LIM, inventory=INV)
    for i in range(30):
        g.admit("ecg__nk")
        g.record("ecg__nk", "files/s/short.edf", "healthy" if i % 10 == 9 else "unhealthy")
    assert g.admit("ecg__nk") is None


def test_declared_has_its_own_outcome():
    r = Guard(limits=LIM, inventory=INV).record("ecg__nk", "files/s/night.edf", "unhealthy")
    assert r["outcome"] == "declared" and "not_applicable" in r


# ---------------------------------------------------------------- limit shapes and the real table

INV2 = {"families": {"f": {"paths": ["a", "b", "c"], "meta": {
    "a": {"width": 512, "height": 512, "frames": 9, "sample_rate": [100, 200]},
    "b": {"width": 128, "height": 128, "frames": 7, "sample_rate": [50]},
    "c": {"duration_s": 60}}}}}
LIM2 = {"img": {"width": {"min": 224}, "height": {"min": 224}, "frames": [2, 9, 10, 11]},
        "sig": {"sample_rate_hz": {"min": 100}}}


def test_min_bound_and_list():
    g = Guard(limits=LIM2, inventory=INV2)
    assert g.declared("img", "a") is None
    assert "width" in g.declared("img", "b")
    assert g.declared("sig", "a") is None, "one channel at an accepted rate is enough"
    assert "sample_rate" in g.declared("sig", "b")


def test_frames_not_in_list():
    inv = {"families": {"f": {"paths": ["x"], "meta": {"x": {"width": 300, "height": 300, "frames": 7}}}}}
    assert "frames" in Guard(limits=LIM2, inventory=inv).declared("img", "x")


def test_the_real_table_parses_and_covers_every_card():
    """Retired encoders keep their entries, so the table may hold more than the cards on disk, never fewer."""
    table = yaml.safe_load(service.LIMITS.read_text())
    cards = {yaml.safe_load(open(f))["id"] for f in glob.glob(str(ENCODERS / "*/*/card.yaml"))}
    assert cards and cards <= set(table)
    assert all("quote" in e for e in table.values())


# ---------------------------------------------------------------- what an answer showed

def test_summary_keeps_labels_events_text_and_never_embedding_values():
    outs = [{"kind": "labels", "scale": "probability", "items": [{"label": "Cardiomegaly", "value": 0.62}]},
            {"kind": "events", "items": [{"label": "N2", "t_start": 0, "t_end": 30}] * 25 + [{"label": "REM"}]},
            {"kind": "text", "text": "x" * 1000},
            {"kind": "embedding", "dim": 1024, "vector": [0.1] * 1024}]
    s = summarize_outputs(outs)
    assert s[0]["items"] == [{"label": "Cardiomegaly", "value": 0.62}]
    assert (s[1]["n"], s[1]["label_counts"], len(s[1]["first"])) == (26, {"N2": 25, "REM": 1}, 20)
    assert len(s[2]["text"]) == 400
    assert s[3] == {"kind": "embedding", "dim": 1024}


def test_summary_of_nothing():
    assert summarize_outputs(None) == []


# ---------------------------------------------------------------- witness

def test_an_encoder_read_inside_its_call_window_is_the_encoders():
    w = Witness("/nonexistent")
    w.encode_window("refs/ecg/rec1.hea", 100.0, 110.0)
    w.note("refs/ecg/rec1.hea", 101.0)        # the encoder reads its input
    w.note("refs/ecg/rec1_0001e.dat", 105.0)  # and a companion signal file
    w.note("refs/ecg/rec1.hea", 300.0)        # the agent opens it later itself
    snap = {r["path"]: r for r in w.snapshot()}
    assert (snap["refs/ecg/rec1.hea"]["n_agent"], snap["refs/ecg/rec1.hea"]["n_encoder"]) == (1, 1)
    assert snap["refs/ecg/rec1_0001e.dat"]["n_agent"] == 0


def test_control_other_files_during_a_call_are_the_agents():
    w = Witness("/nonexistent")
    w.encode_window("refs/ecg/rec1.hea", 100.0, 110.0)
    w.note("tables/diagnosis.csv", 105.0)     # the agent reads a table while the encoder runs
    w.note("refs/ecg/rec2.hea", 105.0)        # another record, same directory
    snap = {r["path"]: r for r in w.snapshot()}
    assert snap["tables/diagnosis.csv"]["n_agent"] == 1
    assert snap["refs/ecg/rec2.hea"]["n_agent"] == 1


def test_notes_aggregate(tmp_path):
    w = Witness(str(tmp_path))
    for p in ("tables/a.csv", "tables/a.csv", "files/s/x.edf"):
        w.note(p)
    assert {r["path"]: r["n"] for r in w.snapshot()} == {"tables/a.csv": 2, "files/s/x.edf": 1}
    assert w.writes == []  # set before watch_writes, so /usage never needs a fallback


# ---------------------------------------------------------------- the deployment record

K1, K2 = "sha256:" + "1" * 64, "sha256:" + "2" * 64
IMG = "sha256:" + "e" * 64


def rec_with(**stages):
    st = {s: {"status": v, "at": "2026-09-25T00:00:00Z", "build_key": K1} for s, v in stages.items()}
    return {"schema": record.SCHEMA, "encoders": {
        "fam__enc": {"build_key": K1, "source_rev": "a" * 40, "image": "ghcr.io/medomni/fam__enc:dev",
                     "image_id": IMG, "built_at": "2026-09-25T00:00:00Z", "stages": st}}}


def test_record_servable_and_ref():
    r = rec_with(L0="PASS", L1="PASS", L2="PASS", L3="PASS")
    assert record.servable(r, "fam__enc") == (True, "ok")
    assert record.ref(r, "fam__enc") == IMG


def test_an_entry_without_image_id_is_not_servable():
    r = rec_with(L2="PASS", L3="PASS")
    del r["encoders"]["fam__enc"]["image_id"]
    assert not record.servable(r, "fam__enc")[0]
    assert record.ref(r, "fam__enc") is None


def test_l3_unverified_is_not_servable():
    assert not record.servable(rec_with(L2="PASS", L3="UNVERIFIED-thin"), "fam__enc")[0]


def test_a_stage_for_another_build_key_is_not_servable():
    r = rec_with(L2="PASS", L3="PASS")
    r["encoders"]["fam__enc"]["stages"]["L2"]["build_key"] = K2
    assert "another build_key" in record.servable(r, "fam__enc")[1]


def test_no_entry_wrong_schema_and_no_file(tmp_path):
    assert not record.servable(rec_with(L2="PASS", L3="PASS"), "other__enc")[0]
    p = tmp_path / "deployed.yaml"
    p.write_text(yaml.safe_dump({"schema": "medomni.deployed/0"}))
    with pytest.raises(ValueError):
        record.load(p)
    assert record.load(tmp_path / "none.yaml") is None


def test_the_real_record_parses():
    rec = record.load(REPO / service.RECORD)
    assert rec and rec["encoders"]
    for e in rec["encoders"]:
        if record.servable(rec, e)[0]:
            assert record.ref(rec, e).startswith("sha256:")


# ---------------------------------------------------------------- scoping and the deployment

VITALS = "clinical-measurement-irregular__labs-summary"
OTHER = "cxr-radiograph-2d__torchxrayvision"
PINS = {"ecg-12lead-500hz-mv__ecgfounder": {"concurrency": 1}, OTHER: {"concurrency": 2}}


def test_scope_serves_exactly_the_inventory():
    rec = rec_with(L2="PASS", L3="PASS")
    s = service.scope(shipped_catalog(), {"encoders": [VITALS, OTHER, "gone__enc"]}, rec, PINS)
    assert sorted(e.id for e in s.catalog.all()) == sorted([VITALS, OTHER])
    assert s.label == "inventory (2 encoders)"
    assert set(s.unservable) == {VITALS, OTHER, "gone__enc"}  # reported, never hidden
    assert s.unservable["gone__enc"] == "no record entry"
    assert s.pins == {OTHER: {"concurrency": 2}}


def test_scope_without_an_inventory_is_everything():
    full = shipped_catalog()
    s = service.scope(full, None, None, PINS)
    assert len(s.catalog) == len(full) and s.pins == PINS and s.unservable == {}
    assert s.label.startswith("unscoped")


def test_the_deployment_keeps_the_file_and_fixes_the_rest(tmp_path):
    doc = yaml.safe_load((REPO / service.DEPLOYMENT).read_text())
    d = service.deployment_for(doc, tmp_path, str(tmp_path), {OTHER: {"concurrency": 2}}, max_live=3)
    assert d.encoders == {OTHER: {"concurrency": 2}}
    assert d.call_log is None and d.admin_api is False and d.stop_on_exit is True
    assert d.max_live_containers == 3 and d.data_root == tmp_path.resolve()
    assert d.encode_timeout_s == doc["encode_timeout_s"]


# ---------------------------------------------------------------- the runner, without Docker

def runner_for(tmp_path, rec=None, self_id="c" * 64):
    d = config.load(None, {"data_root": str(tmp_path), "call_log": None})
    return service.SidecarRunner(d, self_id=self_id, network="atomnet", record=rec, encoders_dir=ENCODERS)


def test_labels_carry_this_service_and_names_differ_by_it(tmp_path):
    one, two = runner_for(tmp_path), runner_for(tmp_path, self_id="d" * 64)
    assert one.labels_for(VITALS)[service.SIDECAR_LABEL] == "c" * 64
    assert one.name_for(VITALS) != two.name_for(VITALS)


def test_the_recorded_image_id_runs_and_the_dev_tag_only_without_one(tmp_path):
    rec = {"schema": record.SCHEMA, "encoders": {VITALS: {"image_id": IMG}}}
    assert runner_for(tmp_path, rec).tag_for(VITALS) == IMG
    assert runner_for(tmp_path, rec).tag_for(OTHER).endswith(f"/{OTHER}:dev")
    assert runner_for(tmp_path).tag_for(VITALS).endswith(":dev")


def test_the_container_joins_the_atom_network(tmp_path):
    r = runner_for(tmp_path)
    box = r.container(VITALS)
    assert isinstance(box, service.SidecarContainer) and box.baked
    assert (box.network, box.volumes_from, box.data_root) == ("atomnet", "c" * 64, str(tmp_path.resolve()))
    assert box.given_name == r.name_for(VITALS) and box.labels == r.labels_for(VITALS)


def test_reaping_removes_only_this_services_containers(monkeypatch):
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="aaa\nbbb\n" if argv[1] == "ps" else "")

    monkeypatch.setattr(service.subprocess, "run", run)
    service.reap_own_encoders("c" * 64)
    assert calls[0][-1] == f"label={service.SIDECAR_LABEL}={'c' * 64}"
    assert calls[1] == ["docker", "rm", "-f", "aaa", "bbb"]


# ---------------------------------------------------------------- /usage, against a fake pool

TestClient = pytest.importorskip("fastapi.testclient").TestClient


class FakePool:
    def __init__(self, status=200, body=None):
        self.status_code, self.body, self.calls = status, body, []

    async def encode(self, encoder_id, body):
        self.calls.append((encoder_id, body))
        answer = self.body or {"encoder_id": encoder_id, "family": body["family"], "healthy": True,
                               "outputs": [{"kind": "labels", "scale": "probability",
                                            "items": [{"label": "x", "value": 0.5}]}],
                               "notes": [], "runtime": {"duration_ms": 1.0}}
        return self.status_code, answer, 0.0, "sha256:fake"

    async def image_id(self, encoder_id):
        return "sha256:fake"

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


@pytest.fixture
def usage_app(tmp_path):
    """An app scoped to one encoder over a synthetic data root, with the guard, witness and call log wired in."""
    data = tmp_path / "workspace/data"
    (data / "tables").mkdir(parents=True)
    (data / "tables/labs.jsonl").write_text('{"x": 1}\n')
    (data / "refs").mkdir()
    (data / "refs/r1.hea").write_text("r1 1 500 10\nr1.dat 16 1 0 0 0 0 0 I\n")
    (data / "refs/r1.dat").write_bytes(b"\0" * 20)

    def make(pool=None, max_calls=300, inventory=None, rec=None):
        inventory = inventory if inventory is not None else {"encoders": [VITALS]}
        scoped = service.scope(shipped_catalog(), inventory, rec, {})
        d = service.deployment_for({}, tmp_path, str(data), scoped.pins, max_live=5)
        pool = pool or FakePool()
        log = service.Calls(tmp_path / "var/calls.jsonl")
        app = service.build_app(d, scoped.catalog, pool, Guard(max_calls=max_calls), Witness(str(data)), log,
                                scoped, rec, data.parent / ".staged")
        return TestClient(app), pool

    return make


def encode(api, path, encoder=VITALS):
    return api.post("/encode", json={"encoder_id": encoder, "path": path})


def test_usage_reports_a_healthy_call(usage_app):
    api, pool = usage_app()
    with api:
        assert encode(api, "tables/labs.jsonl").status_code == 200
        u = api.get("/usage").json()
    assert set(u) == {"status", "encoders", "scope", "witness", "record", "calls", "opened", "submission_writes",
                      "budget", "breaker"}
    assert (u["status"], u["encoders"], u["scope"]) == ("ok", "on", "inventory (1 encoders)")
    assert u["witness"] == "started without sentinel" and u["record"].startswith("absent")
    assert u["budget"] == {"used": 1, "max": 300} and u["breaker"] == {}
    [c] = u["calls"]
    assert (c["encoder_id"], c["status"], c["outcome"], c["healthy"]) == (VITALS, 200, "healthy", True)
    assert c["outputs"] == [{"kind": "labels", "scale": "probability", "items": [{"label": "x", "value": 0.5}], "n": 1}]
    assert len(pool.calls) == 1


def test_the_catalogue_is_scoped(usage_app):
    api, _ = usage_app()
    with api:
        assert [e["id"] for e in api.get("/encoders", params={"runnable": "any"}).json()] == [VITALS]
        assert encode(api, "tables/labs.jsonl", encoder=OTHER).status_code == 404


def test_an_empty_inventory_serves_no_encoder(usage_app):
    api, _ = usage_app(inventory={"encoders": []})
    with api:
        assert api.get("/encoders", params={"runnable": "any"}).json() == []


def test_a_wfdb_signal_file_is_a_bad_request_with_the_fix(usage_app):
    api, pool = usage_app()
    with api:
        r = encode(api, "refs/r1.dat")
        u = api.get("/usage").json()
    assert r.status_code == 400 and "refs/r1.hea" in r.json()["detail"]
    assert (u["calls"][0]["outcome"], u["calls"][0]["hint"]) == ("bad_request", "wfdb data file")
    assert pool.calls == []


def test_a_bad_path_is_logged_and_never_reaches_the_pool(usage_app):
    api, pool = usage_app()
    with api:
        assert encode(api, "../etc/passwd").status_code == 400
        assert encode(api, "tables/none.jsonl").status_code == 400
        u = api.get("/usage").json()
    assert [c["outcome"] for c in u["calls"]] == ["bad_request", "bad_request"]
    assert pool.calls == []


def test_an_upstream_failure_counts_toward_the_breaker(usage_app):
    api, _ = usage_app(pool=FakePool(status=500, body={"error": "boom"}))
    with api:
        assert encode(api, "tables/labs.jsonl").status_code == 502
        [c] = api.get("/usage").json()["calls"]
    assert (c["outcome"], c["undeclared_run"], c["healthy"], c["status"]) == ("error", 1, False, 502)


def test_the_budget_refuses_and_logs_the_refusal(usage_app):
    api, pool = usage_app(max_calls=1)
    with api:
        assert encode(api, "tables/labs.jsonl").status_code == 200
        assert encode(api, "tables/labs.jsonl").status_code == 429
        u = api.get("/usage").json()
    assert u["calls"][1] == {**u["calls"][1], "refused": "budget", "status": 429}
    assert u["budget"] == {"used": 2, "max": 1} and len(pool.calls) == 1


def test_usage_reports_the_record(usage_app):
    rec = {"schema": record.SCHEMA, "encoders": {}}
    api, _ = usage_app(rec=rec)
    with api:
        u = api.get("/usage").json()
    assert u["record"] == {"schema": record.SCHEMA, "unservable": {VITALS: "no record entry"}}


def test_healthz_answers_without_the_operator_routes(usage_app):
    api, _ = usage_app()
    with api:
        assert api.get("/healthz").status_code == 200
        assert api.get("/admin/pool").status_code == 404


# ---------------------------------------------------------------- the image handle Bench looks up

def test_service_fields():
    s = sidecar.SERVICE
    assert (s.name, s.image, s.port, s.url) == ("perception", "medomni-perception", 8899, "http://perception:8899")
    assert s.dockerfile.is_file() and s.dockerfile == REPO / sidecar.DOCKERFILE
    assert s.build_command(REPO) == ["docker", "build", "-f", str(REPO / sidecar.DOCKERFILE),
                                     "-t", "medomni-perception", str(REPO)]


def test_present_asks_docker_and_is_false_without_it(monkeypatch):
    seen, codes = [], [0, 1]

    def run(argv, **kw):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, codes.pop(0))

    monkeypatch.setattr(sidecar.subprocess, "run", run)
    assert sidecar.SERVICE.present() is True and seen[0] == ["docker", "image", "inspect", "medomni-perception"]
    assert sidecar.SERVICE.present() is False

    def missing(argv, **kw):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(sidecar.subprocess, "run", missing)
    assert sidecar.SERVICE.present() is False


def test_the_entry_point_names_the_service():
    meta = tomllib.loads((REPO / "pyproject.toml").read_text())
    target = meta["project"]["entry-points"]["medomni.services"]["perception"]
    assert target == "medomni.perception.sidecar:SERVICE"
    from importlib.metadata import EntryPoint
    assert EntryPoint("perception", target, "medomni.services").load() is sidecar.SERVICE


def test_the_compose_contract_matches_the_service():
    """Studio's renderer writes the service name, image, port and URL atoms use; they must be this service's."""
    text = (REPO / "src/medomni/studio/build/render.py").read_text()
    s = sidecar.SERVICE
    assert f'"image": "{s.image}"' in text and f"PERCEPTION_URL={s.url}" in text and 'services["perception"]' in text


def test_importing_the_package_imports_no_gateway():
    code = "import sys, medomni.perception.sidecar; print(any(m.startswith('medomni.perception.gateway') for m in sys.modules))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


def test_every_copy_in_the_dockerfile_is_allowed_by_its_ignore_file():
    """BuildKit sends only what Dockerfile.dockerignore allows; a COPY of anything else fails the build."""
    here = sidecar.DOCKERFILE.rsplit("/", 1)[0]
    allowed = [line[1:] for line in (REPO / here / "Dockerfile.dockerignore").read_text().splitlines()
               if line.startswith("!")]
    sources = []
    for line in (REPO / sidecar.DOCKERFILE).read_text().splitlines():
        if line.startswith("COPY "):
            sources += line.split()[1:-1]
    assert sources
    for src in sources:
        assert (REPO / src).exists(), src
        assert any(src == a or src.startswith(a + "/") or a.startswith(src + "/") for a in allowed), src
